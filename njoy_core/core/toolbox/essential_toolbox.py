class EssentialToolboxError(Exception):
    pass


class EssentialToolbox:
    @staticmethod
    def passthrough(control):
        return control.state

    @staticmethod
    def not_(control):
        return not control.state

    @staticmethod
    def any(*controls):
        return any([control.state for control in controls])

    @staticmethod
    def not_any(*controls):
        return not any([control.state for control in controls])
