class ProviderPort:
    def __init__(self, mode="NONE"):
        self.mode = mode

    @property
    def available(self):
        return self.mode != "NONE"

    def escalate(self, payload):
        if not self.available:
            return {
                "status": "PROVIDER_UNAVAILABLE",
                "provider_mode": self.mode
            }

        # Future:
        # MEasyMate AI Hub Adapter
        raise NotImplementedError(
            "AI Hub provider is not implemented in CBI V1"
        )
