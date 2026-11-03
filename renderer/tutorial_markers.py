"""Number fixed teaching work slots on the rigid-shell scene renderers."""
from kivy.uix.label import Label
from cube.polyhedral import dot


class TutorialMarkersMixin:
    def __init__(self,**kwargs):
        self._tutorial_reference=None;self._tutorial_targets={};self._tutorial_target_labels={}
        super().__init__(**kwargs)

    def set_tutorial_reference(self,cube):
        self._tutorial_reference=cube
        self._trigger()

    def set_tutorial_targets(self,targets):
        for label in self._tutorial_target_labels.values():self.remove_widget(label)
        self._tutorial_targets=dict(targets);self._tutorial_target_labels={}
        for piece,text in targets.items():
            label=Label(text=str(text),size_hint=(None,None),size=(28,28),font_size='18sp',bold=True,
                        color=(1,.78,.25,1),outline_width=2,outline_color=(.05,.06,.08,1),opacity=0)
            self.add_widget(label);self._tutorial_target_labels[piece]=label
        self._trigger()

    def _draw(self,*args):
        super()._draw(*args)
        for label in self._tutorial_target_labels.values():label.opacity=0
        if not self._tutorial_reference or not self._tutorial_targets or not getattr(self,'_proj',None):return
        if self._move is not None:return
        eye,right,up,factor,cx,cy=self._proj;observation=self.observation_world();candidates={}
        for points,normal,color,slot,layer,start,width in self._surfaces(self._tutorial_reference):
            if start not in self._tutorial_targets or color<0:continue
            if dot(observation.transform(*normal),eye)<=1e-8:continue
            projected=tuple((cx+dot(observation.transform(*p),right)*factor,
                             cy+dot(observation.transform(*p),up)*factor) for p in points)
            a=projected[0]
            for b,c in zip(projected[1:],projected[2:]):
                area=abs((b[0]-a[0])*(c[1]-a[1])-(c[0]-a[0])*(b[1]-a[1]))
                point=((a[0]+b[0]+c[0])/3,(a[1]+b[1]+c[1])/3)
                if area>candidates.get(start,(0,None))[0]:candidates[start]=(area,point)
        for piece,(_area,point) in candidates.items():
            label=self._tutorial_target_labels[piece];label.center=point;label.opacity=1
