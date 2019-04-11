class EssentialToolboxError(Exception):
    pass


class EssentialToolbox:
    @staticmethod
    def passthrough(ctrl_state):
        return ctrl_state

    @staticmethod
    def not_(ctrl_state):
        return not ctrl_state

    @staticmethod
    def any(*ctrl_states):
        return any(ctrl_states)

    @staticmethod
    def not_any(*ctrl_states):
        return not any(ctrl_states)
