from nio.properties import VersionProperty, StringProperty, Property
from nio import TerminatorBlock
from .google_iot_mqtt_base_block import GoogleIoTMQTTBase


class GoogleIoTMQTTPublish(GoogleIoTMQTTBase, TerminatorBlock):
    """A publisher block for the MQTT protocol that is used by google IoT.
    This block will publish messages to a topic."""

    version = VersionProperty("1.0.0")
    topic = StringProperty(title="Topic", default="state",
                           allow_none=False, order=1)
    data_to_publish = Property(title="Data to Publish",
                               default="{{ $text }}", order=2)

    def __init__(self):
        super().__init__()
        self._topic = None

    def configure(self, context):
        super().configure(context)
        self._topic = '/devices/{}/{}'.format(self.device_id(), self.topic())

    def process_signals(self, signals):
        for signal in signals:
            data = self.data_to_publish(signal)
            if isinstance(data, bytes):
                # cannot publish bytes, converting to string
                data = data.decode()

            self.logger.info("Publishing signal to topic '{}': {}".
                             format(self._topic, data))

            response = self._client.publish(topic=self.topic(),
                                            payload=data)
            self.logger.debug(
                "Got response {0}".format(response))
