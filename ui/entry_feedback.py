"""One inline presentation for validation, solver failures and cancellation."""
from functools import wraps
from app.i18n import tr

INPUT_ERRORS={
 'Please enter every sticker':'incomplete',
 'The color counts do not match this puzzle':'counts',
 'The color counts or numbers do not match this puzzle':'counts_numbers',
 'Numbers belong to the ring; colours belong to the corners':'piece',
 'A corner has an impossible colour combination':'piece',
 'A corner has a mirrored orientation':'orientation',
 'A corner has an impossible twist':'orientation',
 'A piece has an impossible color combination or position':'piece',
 'A piece has a mirrored or impossible orientation':'orientation',
 'Repeated color on a piece':'piece','Duplicate piece':'piece',
 'The entered core has an impossible orientation':'orientation',
 'The entered core violates an orientation constraint':'orientation',
 'Position must be restored before adjusting orientation':'illegal',
 'Mirrored or impossible core orientation':'orientation',
 'The entered puzzle is not a legal state':'illegal','Odd orbit permutation':'illegal',
 'The entered pieces violate an orientation or permutation constraint':'illegal',
}


def validation_message(message):
    return tr('poly.error.'+INPUT_ERRORS[message]) if message in INPUT_ERRORS else tr(message)


def _resize_feedback(label,*_):
    if getattr(label,'_entry_feedback_sizing',False):return
    if label.text!=label._entry_feedback_text:
        label.height=label._entry_feedback_base_height
        return
    from ui.widgets import metrics as m
    label._entry_feedback_sizing=True
    try:
        label.text_size=(max(1.,label.width),None)
        label.texture_update()
        label.height=max(label._entry_feedback_base_height,label.texture_size[1]+m.h(8))
    finally:label._entry_feedback_sizing=False


def show_feedback(label,text):
    """Wrap the whole message; restore the normal row height on the next edit."""
    if not hasattr(label,'_entry_feedback_base_height'):
        label._entry_feedback_base_height=label.height
        label.bind(text=_resize_feedback,width=_resize_feedback)
    label._entry_feedback_text=text
    label.text=text
    _resize_feedback(label)


def validation_action(function):
    """Keep each model's checks/highlights; standardize only failure feedback."""
    @wraps(function)
    def validate(self,*args,**kwargs):
        failure=None if function.__name__=='check' else False
        if hasattr(self,'entry_can_edit') and not self.entry_can_edit():return failure
        try:result=function(self,*args,**kwargs)
        except Exception as exc:
            from kivy.logger import Logger
            Logger.exception('Entry validation failed internally')
            if hasattr(self,'_valid'):self._valid=False
            if hasattr(self,'entry_show_error'):
                from services.failures import classify
                self.entry_show_error(str(exc),kind='operation',category=classify(exception=exc))
            return failure
        failed=(result is False or result is None and
                (getattr(self,'_valid',None) is False or function.__name__=='check' and not hasattr(self,'_valid')))
        if failed and hasattr(self,'entry_show_error'):
            label=self.entry_feedback_label()
            self.entry_show_error(label.text if label is not None else tr('poly.error.illegal'))
        return result
    return validate
