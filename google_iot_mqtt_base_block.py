from .client import IoTCoreClient

from nio.properties import (StringProperty, FileProperty, IntProperty)
from nio.util.discovery import not_discoverable


@not_discoverable
class GoogleIoTMQTTBase(object):
    """The base block for Google IoT. This block is responsible for connecting
    to the cloud broker via MQTT paho."""

    project_id = StringProperty(title="Project Id", order=10)
    project_region = StringProperty(title="Project Region", order=11,
                                    default="")
    registry_id = StringProperty(title="Registry Id", order=12)
    device_id = StringProperty(title="Device Id", order=13)

    private_key_path = FileProperty(
        title="Private Key Path", order=14,
        default="[[PROJECT_ROOT]]/etc/google_iot_rsa_private.pem")
    cert_path = FileProperty(
        title="Certificate Path", order=15,
        default="[[PROJECT_ROOT]]/etc/google_iot_cert.pem")

    keep_alive = IntProperty(title="Keep Alive", default=10, advanced=True,
                             order=21)

    def __init__(self):
        super().__init__()
        self._client = None

    def configure(self, context):
        """set up google client properties"""
        super().configure(context)

        self._client = IoTCoreClient(
            self.project_id(),
            self.project_region(),
            self.registry_id(),
            self.device_id(),
            self.private_key_path().value,
            self.cert_path().value,
            self.keep_alive(),
            self.logger,
            on_message=self.on_message
        )

        self._client.connect()

    def stop(self):
        self.disconnect()
        super().stop()

    def connect(self):
        self.logger.debug("Connecting...")
        self.client.connect()

    def disconnect(self):
        self.logger.debug("Disconnecting...")
        self._client.disconnect()

    def on_message(self, client, user_data, message):
        self.logger.debug("on_message, client: {}, message: {}, user data: {}".
                          format(client, message, user_data))
