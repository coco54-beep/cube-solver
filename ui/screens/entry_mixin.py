"""输入页共性动作（混入）。

各族的录入页（标准 N 阶、粽子/镜面/形状、异形、SQ1）都重复实现下面几件事：
    - 一键把魔方设为"已还原态"并写入 app（assign_initial）；
    - 空白录入时预置中心块（方便对位）；
    - 进入本族的拧动页（open_twist）。

把这些收进一个混入，各族只声明差异（钩子），避免以后再"满地开花"漏改。

子类需覆盖的钩子：
    entry_twist_screen           本族拧动页名（None 表示没有）
    entry_can_assign()           现在能否一键还原（默认可以）
    entry_reset_solved()         把工作状态重置为已还原态（不改 app）
    entry_commit_state()         把工作状态写入 app（cube / n / kind 等）
    entry_center_preset()        空白录入时要预置为"已录入"的中心集合
    entry_set_status(text, err)  显示一条状态（各族的状态栏不同）
    entry_can_twist()            现在能否进入拧动页（默认可以）
    entry_prepare_twist()        进入拧动页前的收尾（默认不做事）
"""


class EntryActionsMixin:
    entry_twist_screen = None

    @property
    def entry_state(self):
        state=self.__dict__.get('_entry_task_state')
        if state is None:
            from ui.entry_state import EntryTaskState
            state=self._entry_task_state=EntryTaskState()
            self.bind(on_pre_enter=self._entry_activate,on_pre_leave=self._entry_deactivate,
                      on_enter=self._entry_flush_notice)
        return state

    @property
    def _job(self):
        # Compatibility for model workers; the observable task state owns it.
        return self.entry_state.token

    @_job.setter
    def _job(self,token):
        if token is None:self.entry_state.cancel()
        else:self.entry_state.begin(self.entry_state.requested_phase,token)

    def _entry_activate(self,*_):self.entry_state.active=True

    def _entry_deactivate(self,*_):
        cancel=getattr(self,'_cancel',None)
        if cancel is not None and hasattr(cancel,'set'):cancel.set()
        self.entry_state.active=False;self.entry_state.cancel()
        self._entry_pending_notice=None
        self._entry_notice_delivery=None

    def entry_queue_notice(self,message,kind='input',category=None,locations=None):
        self._entry_notice_delivery=None
        self._entry_pending_notice=(message,kind,category,locations)

    def _entry_flush_notice(self,*_):
        notice=getattr(self,'_entry_pending_notice',None)
        self._entry_pending_notice=None
        if notice is not None:
            from kivy.clock import Clock
            self._entry_notice_delivery=token=object()
            def show(_):
                if getattr(self,'_entry_notice_delivery',None) is not token:return
                if self.manager is not None and self.manager.current!=self.name:return
                if not self.entry_state.active:return
                self._entry_notice_delivery=None;self.entry_show_error(*notice)
            # Screen-specific on_enter may still restore its normal status text.
            # Deliver after that initialization, rather than letting it hide errors.
            Clock.schedule_once(show,0)

    def entry_feedback_label(self):
        return next((getattr(self,name) for name in ('msg','status','hint')
                     if hasattr(getattr(self,name,None),'text')),None)

    def entry_show_error(self,message,kind='input',category=None,locations=None,retry=None):
        from ui.entry_feedback import validation_message,show_feedback
        from services.failures import classify
        from app.i18n import tr
        from ui.entry_problems import problem_locations,update_problem_actions
        previous=getattr(self,'_entry_notice',None)
        category=category or ('cancelled' if kind=='cancelled' else classify(message,default='illegal' if kind=='input' else 'internal'))
        locations_provided=locations is not None
        locations=list(locations) if locations_provided else problem_locations(self,category)
        if previous is not None and message==previous['text'] and kind==previous['kind']:
            text=message;category=previous.get('category',category)
            if not locations_provided:locations=list(previous.get('locations',()))
            if retry is None:retry=previous.get('retry')
        else:
            detail=validation_message(str(message))
            detail=detail.rstrip('。．. \n\r')
            text=tr('entry.cancelled' if category=='cancelled' else 'entry.failure_'+category,detail=detail)
            if category=='illegal' and not locations:text+='\n'+tr('entry.location_unknown')
        self._entry_problem_cursor=-1
        self._entry_notice=dict(kind=kind,text=text,category=category,locations=locations,retry=retry)
        # Draft-based pages regenerate their status label in _refresh().
        if hasattr(self,'_message'):self._message=text
        label=self.entry_feedback_label()
        if label is not None:
            show_feedback(label,text)
            from kivy.app import App
            theme=getattr(App.get_running_app(),'theme',None)
            if theme is not None:label.color=theme.text_muted if kind=='cancelled' else theme.danger
            update_problem_actions(self,label)
        return False

    def entry_gallery_generation(self):
        self._entry_gallery_token = object()
        return self._entry_gallery_token

    def entry_show_exception(self,exc):
        from services.failures import classify
        return self.entry_show_error(str(exc),kind='operation',category=classify(exception=exc))

    def entry_gallery_action(self, token, callback, *args):
        """Ignore queued releases from cards replaced by another selection."""
        if self.manager is not None and self.manager.current!=self.name:return
        if self.entry_can_edit() and getattr(self, '_entry_gallery_token', None) is token:
            callback(*args)

    def entry_help_text(self):
        return (getattr(getattr(self, 'hint', None), 'text', '') or
                getattr(getattr(self, 'status', None), 'text', ''))

    def open_entry_help(self):
        """Show entry guidance when no formula tutorial is provided."""
        if not self.entry_can_edit():
            return
        from kivy.app import App
        from demo.coverage import supports,open_tutorial
        cube=getattr(self,'_cube',None)
        if cube is not None and supports(getattr(cube,'puzzle_kind','cube'),cube.n):
            return open_tutorial(self)
        from kivy.uix.label import Label
        from kivy.uix.popup import Popup
        from ui.widgets.dialogs import theme_popup
        text=self.entry_help_text()
        label = Label(text=text,
                      halign='left', valign='middle')
        label.bind(size=lambda w, *_: setattr(w, 'text_size', w.size))
        popup = Popup(title=self.title.text, content=label, size_hint=(.88, .42))
        theme_popup(popup, App.get_running_app().theme)
        popup.open()
        return popup

    def entry_can_edit(self):
        """Reject conflicting edits while a turn, camera move or solve runs."""
        view=getattr(self,'view',None)
        return not (self.entry_state.locked or
                    getattr(self,'_busy_turn',False) or getattr(self,'_view_busy',False) or
                    getattr(self,'_busy',False) or getattr(self,'_pending_move',None) is not None or
                    getattr(view,'_move',None) is not None or getattr(view,'camera_busy',False) or
                    getattr(view,'_camera_follow_active',False))

    # ---- 钩子（默认实现，供子类覆盖）----
    def entry_can_assign(self):
        return True

    def entry_reset_solved(self):
        raise NotImplementedError

    def entry_commit_state(self):
        pass

    def entry_center_preset(self):
        return set()

    def entry_set_status(self, text, error=False):
        pass

    def entry_can_twist(self):
        return True

    def entry_prepare_twist(self):
        pass

    # ---- 共性动作（只写一次）----
    def assign_initial(self):
        """一键把当前魔方设为已还原态（不跳转，成功不提示）。"""
        if not self.entry_can_edit() or not self.entry_can_assign():
            return
        self.entry_reset_solved()
        self.entry_commit_state()
        self.entry_set_status("")

    def open_twist(self):
        if not self.entry_twist_screen or not self.entry_can_edit() or not self.entry_can_twist():
            return
        self.entry_prepare_twist()
        self.manager.current = self.entry_twist_screen

    def center_preset(self, recorded):
        """把空白录入的中心块并入已录入集合。"""
        return set(recorded) | set(self.entry_center_preset())
