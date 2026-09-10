"""Local prompt-based camera planning for ethanfel's H3 Edit; no API calls."""
import re
import json
import math

DEFAULT_PATH = json.dumps([
    dict(time=0, azimuth=0, elevation=0, distance=1),
    dict(time=0.5, azimuth=45, elevation=10, distance=1),
    dict(time=1, azimuth=90, elevation=0, distance=0.8),
])
PROFILES = {
    '124 frames (~5.17s)': 'scene coverage | 124-frame camera path',
    '243 frames (~10.13s)': 'scene coverage | 243-frame camera path',
    '362 frames (~15.08s)': 'scene coverage | 362-frame camera path',
}
# Legacy framing choices, retained only as metadata for saved workflows.
FRAMINGS = {
    'medium shot': (0.28, 0.56),
    'close-up': (0.53, 0.72),
    'wide shot': (0.097, 0.34),
}
MINIMAX_FORMATS = ['coordinate only', 'coordinate + H3 sections', 'compact JSON', 'compact JSON (no boxes)']
# Every timing in this node is derived from this rate; the video node must use the same one.
FPS = 24.0
ORBIT_DIRECTIONS = ['invert H3 orbit', 'same as HUD']
# Editor limits for the elevation slider. Past about 20 degrees the horizon has already
# left the frame, so the wide range mostly made the control twitchy without adding shots.
ELEVATION_RANGES = {'+/-15': 15, '+/-30': 30, '+/-60': 60, '+/-89': 89}
# Baseline framing shares are written for a 16:9 frame.
REFERENCE_ASPECT = 16 / 9
COMMON_ASPECTS = ((16 / 9, '16:9'), (9 / 16, '9:16'), (1.0, '1:1'), (4 / 3, '4:3'),
                  (3 / 4, '3:4'), (21 / 9, '21:9'), (3 / 2, '3:2'), (2 / 3, '2:3'))



def image_aspect(image):
    """Width / height of a ComfyUI IMAGE batch ([B, H, W, C]), or None."""
    shape = getattr(image, 'shape', None)
    if shape is None or len(shape) < 3:
        return None
    height, width = int(shape[-3]), int(shape[-2])
    if height <= 0 or width <= 0:
        return None
    return width / height

def aspect_label(aspect):
    if aspect is None:
        return '16:9'
    name = min(COMMON_ASPECTS, key=lambda item: abs(item[0] - aspect))
    return name[1] if abs(name[0] - aspect) < 0.04 else f'{aspect:.2f}:1'

def validate_path(raw):
    try:
        path = json.loads(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError('Camera path must be a JSON array.') from exc
    if not isinstance(path, list) or not 2 <= len(path) <= 24:
        raise ValueError('Use between 2 and 24 camera keyframes.')
    result = []
    for item in path:
        if not isinstance(item, dict):
            raise ValueError('Each keyframe must be an object.')
        pose = {}
        for field in ('time', 'azimuth', 'elevation', 'distance'):
            value = item.get(field)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError(f'{field} must be a finite number.')
            pose[field] = float(value)
        if not 0 <= pose['time'] <= 1 or not -89 <= pose['elevation'] <= 89 or not 0.1 <= pose['distance'] <= 4:
            raise ValueError('Allowed ranges: time 0..1, elevation -89..89, distance 0.1..4.')
        result.append(pose)
    if any(b['time'] <= a['time'] for a, b in zip(result, result[1:])):
        raise ValueError('Keyframe times must be strictly increasing.')
    first = result[0]
    if any(abs(first[k] - v) > 1e-6 for k, v in dict(time=0, azimuth=0, elevation=0, distance=1).items()):
        raise ValueError('The anchored source must start at time=0, azimuth=0, elevation=0, distance=1.')
    if sum(abs(b['azimuth'] - a['azimuth']) for a, b in zip(result, result[1:])) > 11520:
        raise ValueError('Azimuth travel exceeds 32 full turns.')
    return result

def _clamp(value, low, high):
    return max(low, min(high, value))

def _choice(value, allowed, fallback):
    """Older saved workflows deserialize new widgets as '' or None; use the default."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return fallback
    if value not in allowed:
        raise ValueError(f'Unknown option {value!r}. Allowed: {", ".join(allowed)}.')
    return value

VERTICAL_FOV = 40.0
REFERENCE_ASPECT_FOV = 16 / 9
DIRECTED_FRAMES = 39
DIRECTED_SETTLE = 0.65
DIRECTED_TAIL_CANDIDATES = 5
# The v15 prompt text is known to work, so the added contract blocks are opt-in. Baseline
# reproduces v15 word for word; extended adds the blocks written after it.
PROMPT_DETAIL = ['v15 baseline', 'extended contracts']
RUNTIME_TASKS = {
    'scene coverage | camera path': None,
    'directed | new camera angle': dict(mode='directed | new camera angle',
                                        prompt_mode='directed | new camera angle',
                                        quality_profile='directed change | 39-frame settle -> 1 image',
                                        frames=DIRECTED_FRAMES),
}
# H3-World (arXiv:2609.01560) binds one text clause to each video latent; a 124-frame clip
# carries 37. Camera keys are I, J, K, L with F for fast. W/A/S/D drive the character and
# are never emitted, because the scene must stay frozen.
H3WORLD_LATENTS_PER_124 = 37
H3WORLD_FAST_DEG_PER_S = 30.0


def horizontal_fov(aspect=None):
    return 2 * math.degrees(math.atan(math.tan(math.radians(VERTICAL_FOV / 2)) * (aspect or REFERENCE_ASPECT_FOV)))


def reversal_indices(path):
    """Keyframes where the orbit changes direction, so the camera has to stop there."""
    return {i for i in range(1, len(path) - 1)
            if (path[i]['azimuth'] - path[i-1]['azimuth']) * (path[i+1]['azimuth'] - path[i]['azimuth']) < 0}


def end_view(net_rotation):
    """The finished angle as a checkable view, leading with the number."""
    turns, rest = divmod(abs(net_rotation), 360.0)
    if rest < 1:
        place = 'back at exactly the reference view'
    else:
        bearing = ('still close to the reference angle' if rest < 20 else
                   'partway between the reference view and a full profile' if rest < 70 else
                   'about a full profile' if rest < 110 else
                   'between a full profile and the far side' if rest < 160 else
                   'the far side, opposite the reference view')
        place = f'{rest:g} degrees around from the reference view, {rest/90:.2f} of a quarter turn, {bearing}'
    laps = f"{turns:g} complete turn{'s' if turns > 1 else ''} and then " if turns else ''
    return laps + place


def parallax_travel(delta_azimuth, delta_elevation, aspect=None):
    """Background travel in words, not boxes: v15 prescribes no screen-space displacement.

    Counting crossings instead of a single sweep is what keeps a 132 degree turn distinct
    from a full 360; any box-shaped measure saturates once the background leaves the frame.
    """
    moves = []
    crossings = abs(delta_azimuth) / horizontal_fov(aspect)
    if abs(delta_azimuth) >= 5:
        side = 'right' if delta_azimuth > 0 else 'left'
        other = 'left' if delta_azimuth > 0 else 'right'
        moves.append(f'background features cross the full frame width to the {side} about {crossings:.1f} times '
                     f'over, entering at the {other} edge as each one leaves'
                     if crossings > 1.15 else
                     f'background features slide about {crossings:.2f} of a frame width to the {side}, with new '
                     f'background entering at the {other} edge')
    if abs(delta_elevation) >= 3:
        moves.append(f"background features also move about {abs(delta_elevation)/VERTICAL_FOV:.2f} of a frame "
                     f"height {'upward' if delta_elevation > 0 else 'downward'}")
    return '; '.join(moves)


def h3world_clause(pan_rate, tilt_rate):
    keys, parts = [], []
    fast = max(abs(pan_rate), abs(tilt_rate)) >= H3WORLD_FAST_DEG_PER_S
    if abs(pan_rate) >= 1.0:
        keys.append('L' if pan_rate > 0 else 'J')
        parts.append(f"pans {'right' if pan_rate > 0 else 'left'}")
    if abs(tilt_rate) >= 1.0:
        keys.append('I' if tilt_rate > 0 else 'K')
        parts.append(f"tilts {'down' if tilt_rate > 0 else 'up'}")
    if not parts:
        return 'the camera holds still', ''
    if fast:
        keys.insert(0, 'F')
    return f"the camera {' and '.join(parts)} {'fast' if fast else 'slowly'}", '+'.join(keys)


def build_h3world_actions(path, end, frames, interpolation):
    latents = max(1, round(frames * H3WORLD_LATENTS_PER_124 / 124))
    span = end / latents
    lines = []
    for index in range(latents):
        t0, t1 = index * span, (index + 1) * span
        a = interpolate_pose(path, min(t0 / max(end, 1e-9), 1.0), interpolation)
        b = interpolate_pose(path, min(t1 / max(end, 1e-9), 1.0), interpolation)
        clause, keys = h3world_clause((b['azimuth'] - a['azimuth']) / span,
                                      (b['elevation'] - a['elevation']) / span)
        lines.append(f"latent {index+1:>2} [{t0:.3f}s-{t1:.3f}s] {keys or '-':<5} {clause}")
    radius = abs(path[-1]['distance'] - path[0]['distance'])
    header = [
        f'H3-World action schedule: {latents} clauses, one per video latent, for {frames} frames at {FPS:g} fps.',
        'Camera keys only. W, A, S and D are never pressed, so the character and the scene stay still.',
        'Limits this cannot express, and where it differs from the orbit in the editor:',
        '  Pan is the camera turning where it stands, not travelling around the subject. Perspective does not '
        'change, surfaces hidden in the first frame are not revealed, and the subject slides out of frame instead '
        'of staying centred.',
        (f'  Camera distance has no key. The {radius:.2f} change of radius in this plan is dropped entirely.'
         if radius > 1e-3 else '  Camera distance has no key, and this plan does not change it.'),
        (f'  H3-World was trained on 124-frame clips with {H3WORLD_LATENTS_PER_124} latents; this profile matches '
         f'that horizon.' if frames == 124 else
         f'  H3-World was trained on 124-frame clips with {H3WORLD_LATENTS_PER_124} latents; this {frames}-frame '
         f'profile is outside it and the latent count is scaled, not verified.'),
        f'  Fast is flagged above {H3WORLD_FAST_DEG_PER_S:g} degrees per second. The paper derives the flag from '
        f'yaw rate but publishes no threshold, so the cutoff is a choice.',
        '  J and L are left and right. The published material does not say which of I and K is up: the '
        'arrow-cluster reading makes I up, one integration table makes I down. The clause text is what H3-World '
        'encodes, so treat it as authoritative and check the letters against your node package.',
        '',
    ]
    return '\n'.join(header + lines)


def interpolate_pose(path, time, interpolation='smooth'):
    """Same per-segment smoothstep as panel.js; also used by regression tests."""
    if time <= path[0]['time']:
        return {k: path[0][k] for k in ('azimuth', 'elevation', 'distance')}
    for a, b in zip(path, path[1:]):
        if time <= b['time']:
            u = (time - a['time']) / (b['time'] - a['time'])
            if interpolation == 'smooth':
                u = u * u * (3 - 2 * u)
            return {k: a[k] + (b[k] - a[k]) * u for k in ('azimuth', 'elevation', 'distance')}
    return {k: path[-1][k] for k in ('azimuth', 'elevation', 'distance')}


def _camera_mode(start, end):
    moves = []
    da = end['azimuth'] - start['azimuth']
    de = end['elevation'] - start['elevation']
    dd = end['distance'] - start['distance']
    if abs(da) > 1e-8:
        moves.append(f"physically move the CAMERA {abs(da):.3f} degrees around the fixed target toward the camera's {'RIGHT' if da > 0 else 'LEFT'}, keeping the lens aimed at that target; the subject itself stays stationary")
    if abs(de) > 1e-8:
        moves.append('physically RAISE the CAMERA along a vertical arc around the fixed target, revealing a higher viewpoint; keep aiming at the target' if de > 0 else 'physically LOWER the CAMERA along a vertical arc around the fixed target, revealing a lower viewpoint; keep aiming at the target')
        if abs(end['elevation']) < 1e-8:
            moves.append('return to the reference elevation offset of 0 degrees; do not pass beyond it')
        else:
            moves.append(f"{'increase' if de > 0 else 'decrease'} elevation offset from {start['elevation']:.3f} to {end['elevation']:.3f} degrees relative to the reference camera")
    else:
        moves.append(f"maintain elevation offset {end['elevation']:.3f} degrees")
    if abs(dd) > 1e-8:
        moves.append(f"{'pull back' if dd > 0 else 'move closer'} from radius {start['distance']:.3f} to {end['distance']:.3f} times the reference radius")
    else:
        moves.append(f"maintain radius {end['distance']:.3f} times the reference radius")
    return '; simultaneously '.join(moves)


def beat_curves(path, interpolation, detail='extended contracts'):
    """Easing belongs at the ends of the take and at reversals, not at every keyframe.

    Smoothstep on each segment decelerates the camera to a full stop at every waypoint,
    which reads as a stutter in a multi-keyframe orbit.
    """
    count = len(path) - 1
    if detail == 'v15 baseline':
        return ['smoothstep' if interpolation == 'smooth' else 'linear'] * count
    if interpolation != 'smooth':
        return ['linear'] * count
    turns = reversal_indices(path)
    curves = []
    for index in range(count):
        opens = index == 0 or index in turns
        closes = index == count - 1 or (index + 1) in turns
        curves.append('ease-in-out' if opens and closes else
                      'ease-in' if opens else 'ease-out' if closes else 'linear')
    return curves


def _direction_contract(path, aspect=None):
    """Frame edges cannot be mirrored; the words left and right can.

    The subject faces the camera, so the subject own left is the viewer right. Naming the
    edge the background enters from gives a check that does not depend on that reading.
    """
    net = path[-1]['azimuth'] - path[0]['azimuth']
    if abs(net) <= 0.5 or reversal_indices(path):
        return ''
    side = 'right' if net > 0 else 'left'
    other = 'left' if side == 'right' else 'right'
    return (f'The camera travels toward the {side} of the frame as the viewer sees it. This is screen {side}, not '
            f'the subject own {side}, and the two are opposite. Two checks that must both hold. First, background '
            f'features slide toward the {side} edge and new background enters from the {other} edge. Second, the '
            f'shot progressively reveals the side of the subject that starts out nearest the {side} edge of the '
            f'frame. If the background enters from the {side} edge instead, the rotation is mirrored and wrong.')


def build_plan(path, end, interpolation, instruction, aspect, detail='extended contracts'):
    segments = []
    for i, (a, b) in enumerate(zip(path, path[1:]), 1):
        segments.append(dict(
            id=f'S{i}', start_s=round(a['time'] * end, 6), end_s=round(b['time'] * end, 6),
            camera_mode=_camera_mode(a, b),
            camera_travel=('right' if b['azimuth'] > a['azimuth'] else 'left' if b['azimuth'] < a['azimuth'] else 'none'),
            signed_orbit_degrees=b['azimuth'] - a['azimuth'],
            speed_curve=beat_curves(path, interpolation, detail)[i-1],
            rotation_deg_per_s=round(abs(b['azimuth']-a['azimuth']) / max((b['time']-a['time'])*end, 1e-9), 3),
            background_travel=parallax_travel(b['azimuth']-a['azimuth'], b['elevation']-a['elevation'], aspect),
            start={k: a[k] for k in ('azimuth','elevation','distance')},
            end={k: b[k] for k in ('azimuth','elevation','distance')},
        ))
    turns = sorted(reversal_indices(path))
    extended = detail != 'v15 baseline'
    tail = (1 - path[-1]['time']) * end
    if tail >= 1 / FPS - 1e-9:
        final = f"Reach the final pose at {path[-1]['time']*end:.6f}s and hold it through {end:.6f}s."
    elif tail > 1e-9:
        final = f"Reach the final pose on the final visible frame at {end:.6f}s; there is no separate visible hold."
    else:
        final = f"Reach the final pose at {end:.6f}s; there is no additional hold."
    plan = dict(
        schema='h3-camera-plan-v15',
        camera_choreography=' Then '.join(f"From {s['start_s']:.3f}s to {s['end_s']:.3f}s: {s['camera_mode']}" for s in segments),
        total_orbit_travel_degrees=sum(abs(b['azimuth']-a['azimuth']) for a,b in zip(path,path[1:])),
        net_orbit_degrees=path[-1]['azimuth']-path[0]['azimuth'], frame=aspect_label(aspect), duration_s=end, fps=FPS,
        reference='The input image is the exact first frame. Preserve its original composition and viewing angle.',
        coordinate_convention=(
            'Azimuth is an unwrapped orbit offset from the reference camera: positive travels toward the '
            "camera's right, negative toward its left while looking at the target. Do not interpret the sign "
            'as the subject own left or right, a pan in place, or a direction for the subject to rotate. '
            'Right and left are the moving camera frame while its lens points at the target, not the editor observer view. Elevation is an orbital angle offset relative to the reference '
            'camera, not an absolute ground angle or a tilt in place. Zero restores the reference elevation. '
            'Radius is distance to the target divided by the starting distance. Keep aiming at the same '
            'subject target, keep focal length fixed and camera roll zero. Do not force the source subject '
            'into a different initial bounding box. Preserve signed full turns; do not replace them with a shorter arc.'),
        preserve='The scene and subjects remain rigid in world space: identity, pose, materials, lighting and physical contacts stay unchanged. Only the camera moves. Hold the captured instant: fire, smoke, water and particles keep their captured shapes and world positions; do not continue their motion.',
        motion=(
            ('Within EACH segment use smoothstep easing: accelerate from zero speed and decelerate to zero '
             'at the next keyframe. Pass through the keyframe without an extra dwell or cut. Angular and '
             'radius offsets ease together; interpolate within each pair of endpoints without overshoot.'
             if not extended else
             'Ease in at the start of the take, hold one constant rate through the middle, ease out at the end. '
             'Do not slow down at the waypoints in between; the camera only comes to a stop where the direction '
             'actually reverses. Angular and radius offsets ease together, without overshoot. No extra dwell or cut.')
            if interpolation == 'smooth' else
            'Interpolate the angular offsets and radius linearly WITHIN EACH segment. Speed may change at '
            'a keyframe when adjacent segments differ in duration or displacement. No extra dwell or cut.'),
        parallax=('Reveal the same scene consistently through physical camera motion. Let perspective and '
                  'occlusion follow the scene geometry; no prescribed screen-space background displacement.'
                  if not extended else
                  'Reveal the same scene consistently through physical camera motion. Let perspective and '
                  'occlusion follow the scene geometry; no screen-space box is prescribed. Over the take, '
                  + (parallax_travel(path[-1]['azimuth']-path[0]['azimuth'],
                                     path[-1]['elevation']-path[0]['elevation'], aspect) or
                     'the camera barely changes angle, so the background stays put')
                  + '. This parallax is the proof the camera really moved; if the background is static the shot is '
                    'wrong, and if it enters from the wrong edge the direction is reversed.'),
        axis_separation=('' if not extended else
            'Rotation and elevation are two separate controls. Every rotation traces a level circle around the '
            'target at whatever height the camera already has, like walking around someone on flat ground: it '
            'leaves camera height untouched. Camera height comes from the elevation offset alone, and from '
            'nothing else.'),
        rotation_direction=_direction_contract(path, aspect) if extended else '',
        completion=('' if not extended else
            f'The camera covers {sum(abs(b["azimuth"]-a["azimuth"]) for a,b in zip(path,path[1:])):g} degrees of '
            f'rotation in {end:.3f}s, an average of '
            f'{sum(abs(b["azimuth"]-a["azimuth"]) for a,b in zip(path,path[1:]))/max(end,1e-9):.1f} degrees per '
            f'second. Hold that rate so the last frame lands on {end_view(path[-1]["azimuth"]-path[0]["azimuth"])}. '
            f'Reaching only part of the way is the most common failure: the amount of travel matters as much as '
            f'its direction, and a small angle must stay small.'
            if sum(abs(b['azimuth']-a['azimuth']) for a,b in zip(path,path[1:])) > 0.5 else ''),
        reversals=('' if not extended else
            'Direction reversals at ' + ', '.join(f"{path[i]['time']*end:.3f}s" for i in turns) +
            f". At each turnaround {'the camera eases down to a full stop and rounds back the other way' if interpolation == 'smooth' else 'the camera holds its speed into the turn, changes direction and holds it out again'}"
            ': no hard flick, no whip pan, no cut, and the background parallax reverses with it.' if turns else ''),
        segments=segments, final=final,
        forbid='No cuts, subject rotation, subject animation, digital zoom, lighting changes, or visible planning annotations.',
        instruction=instruction.strip() or 'Preserve the source scene.',
        sound='Silence.',
    )
    if not extended:
        # Baseline must serialise exactly like v15, so the added keys are removed rather
        # than left empty: the JSON formats render every key.
        for key in ('axis_separation', 'rotation_direction', 'completion', 'reversals'):
            plan.pop(key, None)
        for segment in plan['segments']:
            segment.pop('rotation_deg_per_s', None)
            segment.pop('background_travel', None)
    return plan


def coordinate_anchor(raw):
    """Keep literal L/T/W/H syntax. Empty means the image extent, not a guessed subject."""
    raw = str(raw or '').strip()
    if not raw:
        return {'kind': 'reference_image', 'box': '[L=0.000, T=0.000, W=1.000, H=1.000]',
                'instruction': 'The complete reference image occupies [L=0.000, T=0.000, W=1.000, H=1.000]. Preserve its initial composition. This is the image boundary, not a subject bounding box.'}
    number = r'([+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?)'
    pattern = r'\[\s*L\s*=\s*'+number+r'\s*,\s*T\s*=\s*'+number+r'\s*,\s*W\s*=\s*'+number+r'\s*,\s*H\s*=\s*'+number+r'\s*\]'
    match = re.fullmatch(pattern, raw)
    if not match:
        raise ValueError('subject_box must use [L=0.516, T=0.148, W=0.071, H=0.249], or be empty.')
    l,t,w,h = map(float, match.groups())
    if not all(math.isfinite(v) for v in (l,t,w,h)) or min(l,t)<0 or min(w,h)<=0 or l+w>1+1e-9 or t+h>1+1e-9:
        raise ValueError('subject_box must have positive size and stay within the normalized image.')
    # Preserve supplied precision rather than silently rounding small boxes to zero.
    box = '[L='+match[1]+', T='+match[2]+', W='+match[3]+', H='+match[4]+']'
    return {'kind': 'user_subject', 'box': box,
            'instruction': 'In the reference first frame, the main subject occupies '+box+'. Use this region to identify the fixed orbit target. It defines the starting framing, not a forced box for every subsequent frame. Let the requested camera motion determine subsequent perspective and size.'}


def plan_text(plan, sections=False):
    lines=[plan['camera_choreography'], plan['reference'], plan['coordinate_anchor']['instruction'],
           plan['coordinate_convention']]
    lines += [plan[k] for k in ('axis_separation','rotation_direction','completion','reversals') if plan.get(k)]
    lines += [plan['preserve'], plan['motion'], plan['parallax']]
    for s in plan['segments']:
        row = f"[{s['start_s']:.6f}s-{s['end_s']:.6f}s] {s['camera_mode']}"
        if 'rotation_deg_per_s' in s:
            if s['rotation_deg_per_s'] > 0.5:
                row += f"; rotation rate {s['rotation_deg_per_s']:.1f} degrees per second"
            if s['background_travel']:
                row += f"; {s['background_travel']}"
            row += f"; speed curve {s['speed_curve']}"
        lines.append(row + '.')
    lines.extend([plan['final'],plan['forbid'],'Additional direction: '+plan['instruction']])
    text='\n'.join(lines)
    if not sections:
        return text+'\nSilence.'
    return (
        'subject_definitions:\n<Picture 1> is the exact reference first frame.\n\n'
        f"summary:\nOne continuous camera move over {plan['duration_s']:.6f}s at {FPS:g} fps.\n\n"
        'retention_analysis:\n<Picture 1>: preserve the subjects and scene in world space.\n\n'
        'detailed_description:\n'+text+'\n\noverall_soundscape:\nSilence.\n\nnon_diegetic_music:\nN/A'
    )


def compile_camera(raw, profile, interpolation, instruction, framing=None, minimax_format=None,
                   reference_image=None, elevation_range=None, orbit_direction=None, subject_box=None,
                   runtime_task=None, prompt_detail=None):
    if profile not in PROFILES or interpolation not in ('smooth','linear'):
        raise ValueError('Unknown duration profile or interpolation.')
    framing=_choice(framing, FRAMINGS, 'medium shot')
    minimax_format=_choice(minimax_format, MINIMAX_FORMATS, 'coordinate only')
    elevation_range=_choice(elevation_range, ELEVATION_RANGES, '+/-30')
    orbit_direction=_choice(orbit_direction, ORBIT_DIRECTIONS, 'invert H3 orbit')
    runtime_task=_choice(runtime_task, RUNTIME_TASKS, 'scene coverage | camera path')
    prompt_detail=_choice(prompt_detail, PROMPT_DETAIL, 'v15 baseline')
    task=RUNTIME_TASKS[runtime_task]
    hud_path=validate_path(raw)
    sign=-1 if orbit_direction=='invert H3 orbit' else 1
    # Calibrate prompt-side orbit; leave the saved HUD trajectory untouched.
    path=[dict(p, azimuth=p['azimuth']*sign) for p in hud_path]
    if task:
        # Upstream times this profile as frames / fps and settles at 65 percent of that.
        frames=task['frames']; clip=frames/FPS; end=clip*DIRECTED_SETTLE
    else:
        frames=int(profile.split()[0]); end=(frames-1)/FPS
    aspect=image_aspect(reference_image) if reference_image is not None else None
    net=path[-1]['azimuth']-path[0]['azimuth']; turn=abs(net)%360
    arc=360.0 if turn<1e-6 and abs(net)>1e-6 else _clamp(turn,15.0,360.0)
    # Upstream only engages loop closure at exactly 360 degrees with the frame anchor.
    # It then VAE-encodes the source a second time and pins the last frame to it, which
    # forces the full turn through the latent instead of relying on prompt text alone.
    # Require the height and the radius to return too, or the final frame would not match.
    closes=(math.isclose(arc,360.0,abs_tol=1e-3)
            and math.isclose(path[0]['elevation'],path[-1]['elevation'],abs_tol=0.5)
            and math.isclose(path[0]['distance'],path[-1]['distance'],abs_tol=0.01))
    closes = closes and not task
    if task:
        instruction=(f'Settled tail: complete the whole camera move by {end:.3f}s and then hold the new framing '
                     f'perfectly still, with no drift, through {frames/FPS:.3f}s. The still tail is what the final '
                     f'image is taken from, so the last {DIRECTED_TAIL_CANDIDATES} frames must be identical and '
                     f'sharp. ' + (instruction or '').strip()).strip()
    if closes:
        instruction=(f'Reference alignment: <Picture 1> is the frame at 0.000s. <Picture 2> is the same image '
                     f'again and is the frame at {end:.3f}s. The camera travels the whole way round and returns '
                     f'precisely to the <Picture 2> viewpoint, so the last frame matches the first exactly. '
                     f'Passing through only part of the circle and stopping short leaves the final frame wrong. '
                     + (instruction or '').strip()).strip()
    plan=build_plan(path,end,interpolation,instruction,aspect,prompt_detail)
    plan['coordinate_anchor']=coordinate_anchor(subject_box)
    compiled=plan_text(plan,sections=True)
    minimax=(json.dumps(plan,ensure_ascii=False,indent=2) if minimax_format in ('compact JSON', 'compact JSON (no boxes)')
             else plan_text(plan,sections=minimax_format=='coordinate + H3 sections'))
    options={
        'mode':task['mode'] if task else 'scene coverage | canonical camera path','show_overrides':True,
        'prompt_mode':task['prompt_mode'] if task else 'directed | frozen scene coverage',
        'quality_profile':task['quality_profile'] if task else PROFILES[profile],
        'primary_image_role':'edit | strong scene anchor (FL2VA)','reference_mode':'none (source only)',
        'source_fit':'crop center','semantic_resolution':1024,'native_reference_size':'match output area',
        'coverage_views':len(path),'coverage_arc_degrees':arc,
        'coverage_direction':'clockwise / camera right' if net>=0 else 'counterclockwise / camera left',
        'coverage_hold_frames':1,'coverage_loop_closure':bool(closes),
    }
    # Metadata only. Generic H3 Edit coverage windows cannot describe an arbitrary path.
    storyboard=dict(plan,path=hud_path,model_path=path,orbit_direction=orbit_direction,subject_framing=framing,
                    framing_note='Legacy preset retained as metadata only; no measured subject box is available.',
                    prompt_control='semantic instructions, not geometric conditioning')
    notes=[]
    tail=(1-path[-1]['time'])*end
    if 1e-9 < tail < 1/FPS-1e-9:
        notes.append('Final hold is shorter than one frame; no separate visible hold is requested. The saved path is unchanged.')
    if any(abs(p['elevation'])>ELEVATION_RANGES[elevation_range] for p in path):
        notes.append('Some keyframes exceed the selected editor slider range; their saved values are preserved.')
    if closes:
        notes.append('Loop closure ON: the path returns to its start, so the source image is pinned to the final '
                     'frame as Picture 2 and the full turn is enforced by the latent, not only by the prompt.')
    if task:
        notes.append(f'Directed task: the profile widget is ignored, the move completes by {end:.3f}s and the '
                     f'decoder picks one image from the last {DIRECTED_TAIL_CANDIDATES} frames.')
    info=(f'v16 | {prompt_detail} | {runtime_task} | {orbit_direction} | {frames} frames at {FPS:g} fps ({frames/FPS:.3f}s). '
          'Native H3: connect minimax_prompt, length and fps. H3 Edit: connect compiled_prompt AND options. '
          'Decode the full video with the video VAE, not the calibrated scene-coverage decoder. '
          'Literal [L,T,W,H] anchors are included. Empty subject_box uses the full image boundary only; enter a measured subject box to identify the orbit target. '
          'Legacy compact JSON (no boxes) is retained as a name; all formats now include the coordinate anchor. '
          'Prompt guidance only; angular accuracy still depends on the model. '+' '.join(notes))
    return (compiled,options,json.dumps(storyboard,ensure_ascii=False,indent=2),info,minimax,frames,FPS,
            build_h3world_actions(path,end,frames,interpolation))


class H3CameraEditor:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            'required': {
                'camera_trajectory': ('STRING', {'default': DEFAULT_PATH, 'multiline': True, 'tooltip':
                    'A trajetória em JSON, escrita pelo painel acima. Cada keyframe tem time de 0 a 1, azimuth e '
                    'elevation em graus, e distance como múltiplo do raio inicial. Dá para editar à mão. O primeiro '
                    'keyframe tem de ser time=0, azimuth=0, elevation=0, distance=1: ele é a imagem original.'}),
                'profile': (list(PROFILES), {'tooltip':
                    'Duração do vídeo, em frames a 24 fps. TODOS os tempos do plano saem daqui: os instantes dos '
                    'keyframes, as faixas de cada trecho e a duração escrita no prompt. Por isso ligue as saídas '
                    'length e fps na geração, em vez de digitar os números à mão em dois lugares. A tarefa de ângulo '
                    'único ignora este widget e usa 39 frames.'}),
                'interpolation': (['smooth', 'linear'], {'tooltip':
                    'smooth: a câmera suaviza a entrada e a saída da tomada e mantém taxa constante no meio, parando '
                    'só onde o sentido do giro inverte. linear: uma taxa constante do primeiro ao último frame.'}),
                'instruction': ('STRING', {'default': '', 'multiline': True, 'tooltip':
                    'Texto livre, acrescentado UMA vez no fim do prompt. Escreva só o que o node não tem como saber: '
                    'cenário, qual é o alvo quando há mais de uma pessoa, referência de estilo. Não repita o que já '
                    'sai pronto (cena congelada, primeira imagem como referência, mira travada, roll zero, ângulos, '
                    'tempos, tomada única sem cortes). Cuidado com contradição: escrever "raio constante" enquanto um '
                    'keyframe muda a distância faz o prompt afirmar duas coisas opostas.'}),
            },
            'optional': {
                'subject_framing': (list(FRAMINGS), {'default': 'medium shot', 'tooltip':
                    'Quanto o sujeito ocupa do quadro NA IMAGEM ORIGINAL. close-up: cabeça e ombros, 53% da largura. '
                    'medium shot: cintura para cima, 28%. wide shot: corpo inteiro ao longe, 9,7%. Calibrado contra '
                    'as caixas do tutorial da MiniMax. Errar aqui põe todas as coordenadas fora de escala.'}),
                'minimax_format': (MINIMAX_FORMATS, {'default': 'coordinate only', 'tooltip':
                    'A redação da saída minimax_prompt. coordinate only: bloco de coordenadas em texto. '
                    'coordinate + H3 sections: o mesmo dentro das seções do H3. compact JSON: objeto JSON, quase sem '
                    'prosa e com um terço das palavras. compact JSON (no boxes): só parâmetros de câmera, sem caixa '
                    'de tela. Prompt maior não é automaticamente melhor: compare na mesma trajetória.'}),
                # Connect the same LoadImage the workflow already uses: the panel shows it as
                # the reference card and the prompt picks up the real frame aspect.
                'reference_image': ('IMAGE', {'tooltip':
                    'Ligue o MESMO LoadImage que alimenta o source_image do H3 Edit. A foto aparece no painel sozinha '
                    'e a proporção real do quadro entra no prompt. Sem isso, tudo é normalizado para 16:9, o que erra '
                    'a escala em imagens retrato.'}),
                'elevation_range': (list(ELEVATION_RANGES), {'default': '+/-30', 'tooltip':
                    'Alcance do controle de elevação, e com ele a sensibilidade do arraste vertical. O horizonte já '
                    'sai do quadro por volta de 20 graus, então +/-89 espalha uma faixa quase toda inútil pelo slider '
                    'inteiro. Reduzir o alcance NUNCA reescreve keyframe: um ponto em 70 graus continua em 70 e o '
                    'slider se abre para caber nele.'}),
                'orbit_direction': (ORBIT_DIRECTIONS, {'default': 'invert H3 orbit', 'tooltip':
                    'Calibração do sentido entre o que o painel desenha e o que o H3 entrega. Se o vídeo girar para o '
                    'lado oposto ao do painel, troque aqui. Não altera a trajetória salva.'}),
                'runtime_task': (list(RUNTIME_TASKS), {'default': 'scene coverage | camera path', 'tooltip':
                    'A primeira opção entrega VÍDEO, com a duração vindo do widget profile. A segunda entrega UMA '
                    'IMAGEM de um novo ângulo: fixa 39 frames, completa o movimento em 65% do clipe e segura o '
                    'enquadramento imóvel no resto, porque é dessa cauda parada que o decodificador tira a imagem '
                    'final. Também tem botão na barra Testes do painel.'}),
                'prompt_detail': (PROMPT_DETAIL, {'default': 'v15 baseline', 'tooltip':
                    'v15 baseline: o prompt sai exatamente como na versão anterior, que já estava funcionando. '
                    'extended contracts: acrescenta separação de eixos, teste de direção por borda de quadro, '
                    'completude do giro, graus por segundo e magnitude de paralaxe. Quase o dobro de palavras, então '
                    'é opcional. Também tem botão na barra Testes do painel.'}),
                'subject_box': ('STRING', {'default': '', 'multiline': False, 'tooltip':
                    'Onde o sujeito está na imagem original, no formato [L=0.516, T=0.148, W=0.071, H=0.249]. Vazio '
                    'usa os limites da imagem inteira, de propósito, sem chutar uma caixa. Preencha se o sujeito '
                    'estiver bem fora do centro.'}),
            },
        }
    OUTPUT_TOOLTIPS = (
        'Prompt em prosa, nas seções do H3. Ligue no compiled_prompt do Text Encode H3 Edit.',
        'As 13 chaves que o encoder do H3 Edit lê. OBRIGATÓRIO junto com o prompt: qualquer chave ausente faz o '
        'upstream cair para os widgets legados escondidos dele, que guardam valores velhos de workflows salvos.',
        'Tabela de storyboard em JSON: proporção, duração, a trajetória crua e cada trecho com modo de câmera, '
        'curva de velocidade e as poses de início e fim. Serve para scripts ou para montar o mapa de rota.',
        'Diagnóstico legível. Ligue num PreviewText. Mostra a versão, a tarefa ativa, a contagem de frames, avisos '
        'de keyframes fora do alcance do slider e se a loop closure está ligada.',
        'A mesma trajetória na redação escolhida em minimax_format. É ALTERNATIVA ao compiled_prompt, nunca '
        'adicional: ligue uma ou outra na mesma entrada.',
        'Contagem de frames contra a qual o plano foi cronometrado. Ligue na contagem de frames da geração. Se a '
        'geração rodar com outro valor, a coreografia descreve uma cena que não existe.',
        'Taxa de quadros, 24. Ligue no fps do node de vídeo. Sai como FLOAT porque é o que o CreateVideo aceita.',
        'Cronograma de ações para o H3-World: uma cláusula de texto por latente, 37 num clipe de 124 frames, com a '
        'coluna de teclas ao lado. Atenção aos limites, que a própria saída declara no cabeçalho: pan não é órbita, '
        'a distância não tem tecla, e só 124 frames é horizonte treinado.',
    )
    RETURN_TYPES = ('STRING', 'H3EDIT_OPTIONS', 'STRING', 'STRING', 'STRING', 'INT', 'FLOAT', 'STRING')
    RETURN_NAMES = ('compiled_prompt', 'options', 'storyboard_json', 'info', 'minimax_prompt', 'length', 'fps',
                    'h3world_actions')
    FUNCTION = 'run'
    CATEGORY = 'Bruxos do VFX/Camera H3'
    DESCRIPTION = (
        '#bruxosdovfx | Planejador visual de câmera para o MiniMax H3. Arraste a câmera na esfera, marque '
        'keyframes na timeline, e o node compila a trajetória em prompts.\n\n'
        'LIGAÇÃO MÍNIMA: compiled_prompt E options no Text Encode H3 Edit, a sua imagem em reference_image, e '
        'length e fps nos nodes de geração e de vídeo.\n\n'
        'Ele compila PROMPTS, não embeddings de câmera. Não há adaptador geométrico: o H3 continua livre para '
        'errar ângulo, tempo e escala. A única função que age fora do prompt é a loop closure, que liga sozinha '
        'quando a trajetória fecha 360 graus na mesma altura e distância, e aí crava o último frame na imagem de '
        'origem.\n\n'
        'Decodifique o resultado com o VAE de vídeo H3, não com o decodificador calibrado de scene coverage.'
    )

    @classmethod
    def VALIDATE_INPUTS(cls, subject_framing=None, minimax_format=None, elevation_range=None, orbit_direction=None,
                        runtime_task=None, prompt_detail=None):
        # Naming these inputs here turns off ComfyUI's strict combo check for them, so a
        # workflow saved before these widgets existed still loads instead of failing with
        # "Value not in list: subject_framing: ''". Empty means "use the default".
        for value, allowed in ((subject_framing, FRAMINGS), (minimax_format, MINIMAX_FORMATS),
                               (elevation_range, ELEVATION_RANGES), (orbit_direction, ORBIT_DIRECTIONS),
                               (runtime_task, RUNTIME_TASKS), (prompt_detail, PROMPT_DETAIL)):
            if value is None or (isinstance(value, str) and not value.strip()):
                continue
            if value not in allowed:
                return f'Unknown option {value!r}. Allowed: {", ".join(allowed)}.'
        return True

    def run(self, camera_trajectory, profile, interpolation, instruction, subject_framing=None,
            minimax_format=None, reference_image=None, elevation_range=None, orbit_direction=None, subject_box=None,
            runtime_task=None, prompt_detail=None):
        return compile_camera(camera_trajectory, profile, interpolation, instruction, subject_framing,
                              minimax_format, reference_image, elevation_range, orbit_direction, subject_box,
                              runtime_task, prompt_detail)

NODE_CLASS_MAPPINGS = {'H3LocalCameraEditor': H3CameraEditor}
NODE_DISPLAY_NAME_MAPPINGS = {'H3LocalCameraEditor': 'Camera H3 da Bruxos do VFX'}
