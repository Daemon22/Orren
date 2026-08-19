
class BadService:
    def process(self):
        raise RuntimeError("Intentional failure for adversarial test")
