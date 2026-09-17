"""Reference-neutral camera prose for existing text-encoder workflows."""

def camera_prompt(plan):
    # Whitelist camera geometry: never serialize scene retention, user action,
    # reference tokens, end-frame anchoring or the uncalibrated HUD trajectory.
    path = plan['model_path']
    duration = plan['duration_s']
    lines = ['Camera direction:',
        'One continuous shot. Camera timing controls only the viewpoint; subject and scene actions follow the scene prompt.',
        'Orbit offsets are relative to the initial camera: positive toward camera right, negative toward camera left while looking at the target. Preserve signed full turns. Elevation is a physical orbital rise/fall; distance is a radius ratio, not digital zoom.',
        'Keep the lens aimed at the same subject, allowing its action to continue. Keep focal length fixed and camera roll zero.']
    if plan['coordinate_anchor']['kind']=='user_subject':
        lines.append('Initial subject region: '+plan['coordinate_anchor']['box']+'. This identifies the target at the start, not a fixed pose or bounding box throughout the shot.')
    lines.append('Camera interpolation: '+plan['motion'])
    for a,b in zip(path,path[1:]):
        start=a['time']*duration;end=b['time']*duration
        if all(a[k]==b[k] for k in ('azimuth','elevation','distance')):
            lines.append(f'{start:.3f}s–{end:.3f}s: hold the camera viewpoint; the scene action continues.')
        else:
            lines.append(f"{start:.3f}s–{end:.3f}s: camera orbit {a['azimuth']:g}° → {b['azimuth']:g}°, elevation {a['elevation']:g}° → {b['elevation']:g}°, radius {a['distance']:g} → {b['distance']:g}.")
    last=path[-1]['time']*duration
    if last < plan['last_frame_s']-1e-6:
        lines.append(f"{last:.3f}s–{plan['last_frame_s']:.3f}s: hold only the final camera viewpoint while the action continues.")
    return '\n'.join(lines)


class CameraPromptCompose:
    CATEGORY='bruxosdovfx/Camera H3'
    FUNCTION='compose'
    RETURN_TYPES=('STRING',)
    RETURN_NAMES=('prompt',)
    DESCRIPTION='PT: Combina seu prompt com camera_prompt para o encoder de um workflow existente. Não altera imagens, modelo ou condicionamento. EN: Combines your prompt with camera_prompt for an existing workflow encoder. Does not change images, model or conditioning.'
    @classmethod
    def INPUT_TYPES(cls):
        return {'required':{
            'scene_prompt':('STRING',{'multiline':True,'default':'','tooltip':'PT: Seu prompt de cena e ação; aceita conexão STRING. EN: Your scene and action prompt; accepts a STRING connection.'}),
            'camera_prompt':('STRING',{'forceInput':True,'tooltip':'PT: Conecte a saída camera_prompt do Camera H3. EN: Connect Camera H3 camera_prompt output.'}),
            'enabled':('BOOLEAN',{'default':True,'tooltip':'PT: Desligado devolve seu texto original para comparação. EN: Off returns your original text for comparison.'})}}
    def compose(self,scene_prompt,camera_prompt,enabled=True):
        if not enabled or not camera_prompt.strip():
            return (scene_prompt,)
        # Avoid appending the same block again when the output is passed through twice.
        if scene_prompt == camera_prompt or scene_prompt.endswith('\n\n'+camera_prompt):
            return (scene_prompt,)
        return (scene_prompt+('\n\n' if scene_prompt else '')+camera_prompt,)
