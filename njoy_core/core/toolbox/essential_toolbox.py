class EssentialToolboxException(Exception):
    pass


class EssentialToolbox:
    @staticmethod
    def passthrough(value):
        return value

    @staticmethod
    def not_(value):
        if not isinstance(value, bool):
            raise EssentialToolboxException("The NOT control only accepts a boolean input value")
        return not value

    @staticmethod
    def any(*values):
        return any(values)

    @staticmethod
    def not_any(*values):
        return not any(values)
