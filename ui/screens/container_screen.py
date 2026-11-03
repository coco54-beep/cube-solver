"""Container entry uses rigid coloured shape cards, including directions."""
from ui.screens.fisher_skewb_screen import FisherSkewbScreen
from cube.container import ContainerCube,appearance


class ContainerScreen(FisherSkewbScreen):
    cube_class=ContainerCube
    appearance=staticmethod(appearance)
    hint_key='container.hint'

    def _refresh(self):
        super()._refresh()
        if self._cube is not None:
            self.demo_button.disabled=False;self.demo_button.opacity=1
