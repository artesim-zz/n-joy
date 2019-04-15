class EssentialToolboxError(Exception):
    pass


class EssentialToolbox:
    @staticmethod
    def passthrough(ctrl_state):
        if len(ctrl_state) != 1:
            raise EssentialToolboxError("EssentialToolbox.passthrough is a unary operator")
        return list(ctrl_state.values())[0]

    @staticmethod
    def not_(ctrl_state):
        if len(ctrl_state) != 1:
            raise EssentialToolboxError("EssentialToolbox.not_ is a unary operator")
        return not list(ctrl_state.values())[0]

    @staticmethod
    def any(ctrl_states):
        return any([value for value in ctrl_states.values()])

    @staticmethod
    def not_any(ctrl_states):
        tmp = not any([value for value in ctrl_states.values()])
        return tmp
