"""Locate known input errors and expose consistent, input-preserving recovery."""
from app.i18n import tr


def problem_locations(screen,category):
    cells=getattr(screen,'_error_cells',())
    if cells:return [dict(face=f,row=r,column=c) for f,r,c in sorted(cells)]
    if category!='incomplete':return []
    state=getattr(screen,'_mx_state',None)
    if state:
        return [dict(block=bi,cell=ci) for bi,b in enumerate(state['blocks']) for ci,c in enumerate(b['cells'])
                if c['world'] is None or c['color']<0]
    state=getattr(screen,'_six_state',None)
    if state:
        return [dict(six_face=face,index=i) for face,view in enumerate(state['views'])
                for i,cell in enumerate(view) if cell[0]==-1]
    data=getattr(screen,'_data',None)
    if isinstance(data,dict):
        return [dict(face=f,row=r,column=c) for f,g in data.items() if isinstance(g,list)
                for r,row in enumerate(g) if isinstance(row,list) for c,v in enumerate(row) if v in ('',None,-1)]
    cube=getattr(screen,'_cube',None)
    colors=getattr(cube,'colors',())
    if isinstance(colors,list):return [dict(sticker=i) for i,c in enumerate(colors) if c==-1]
    return []


def focus_problem(screen):
    if not screen.entry_can_edit():return
    locations=getattr(screen,'_entry_notice',{}).get('locations',[])
    if not locations:return
    cursor=(getattr(screen,'_entry_problem_cursor',-1)+1)%len(locations);screen._entry_problem_cursor=cursor
    loc=locations[cursor]
    if {'face','row','column'}<=loc.keys() and hasattr(screen,'_error_cells'):
        all_cells=set(screen._error_cells);screen._error_cells={(loc['face'],loc['row'],loc['column'])}
        if hasattr(screen,'_focus_error_face'):screen._focus_error_face()
        screen._error_cells=all_cells|screen._error_cells
        screen._entry_problem_pivot=(loc['face'],loc['row'],loc['column'])
        if hasattr(screen,'_refresh_view'):screen._refresh_view()
        if hasattr(screen.view,'set_entry_pivot'):screen.view.set_entry_pivot((loc['face'],loc['row'],loc['column']))
    elif 'block' in loc and hasattr(screen,'_mx_selected'):
        screen._paint_enabled=False;screen._mx_selected=(loc['block'],loc['cell'])
        screen._clear_options();screen._refresh();screen._load_assemblies()
    elif 'sticker' in loc and hasattr(screen,'view'):
        if hasattr(screen,'focus_sticker'):screen.focus_sticker(loc['sticker'])
        else:
            if hasattr(screen,'_set_face_camera'):screen._set_face_camera(screen._cube.geometry.stickers[loc['sticker']].face)
            screen.view.selected=loc['sticker'];screen.view.refresh()
    elif 'six_face' in loc:
        screen.change_face(loc['six_face']);screen._selected=(loc['index'],);screen._refresh()
    elif 'observation_face' in loc:
        layout=getattr(screen,'_color_layout',None)
        if layout is not None and getattr(layout,'active',False):layout.change_face(loc['observation_face'])
        elif hasattr(screen,'change_face'):screen.change_face(loc['observation_face'])


def update_problem_actions(screen,label):
    from ui.widgets.buttons import UIButton
    from ui.widgets.layouts import ResponsiveBoxLayout
    parent=label.parent
    if parent is None or getattr(parent,'orientation',None)!='vertical':return
    row=getattr(screen,'_entry_problem_actions',None)
    if row is None or row.parent is not parent:
        row=screen._entry_problem_actions=ResponsiveBoxLayout(height_px=40,gap_px=5)
        locate=UIButton(icon_name='target');retry=UIButton(icon_name='reset');edit=UIButton(icon_name='back')
        row.locate=locate;row.retry=retry
        locate.bind(on_release=lambda *_:focus_problem(screen))
        def try_again(*_):
            if screen.entry_can_edit():
                callback=screen._entry_notice.get('retry') or getattr(screen,'start_solve',None) or getattr(screen,'solve',None)
                if callback:callback()
        retry.bind(on_release=try_again)
        def dismiss(*_):
            row._height_px=0;row.opacity=0;row.disabled=True;row._sync_metrics()
        edit.bind(on_release=dismiss)
        for w in (locate,retry,edit):row.add_widget(w)
        parent.add_widget(row,index=parent.children.index(label))
        label.bind(text=lambda w,value:dismiss() if value!=getattr(screen,'_entry_notice',{}).get('text') else None)
    notice=screen._entry_notice
    row._height_px=0 if notice['category']=='cancelled' else 40
    row.opacity=1 if row._height_px else 0;row.disabled=not bool(row._height_px)
    row.locate.disabled=not notice['locations'];row.retry.disabled=notice['category'] in ('incomplete','illegal')
    row._sync_metrics()
