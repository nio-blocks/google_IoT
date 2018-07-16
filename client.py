import datetime
import ssl
import jwt
import paho.mqtt.client as mqtt


def NOOP(*a, **k):
    pass


class IoTCoreClient():

    def __init__(self,
                 gcp_project_id,
                 gcp_region,
                 gcp_registry,
                 device_id,
                 priv_key_file,
                 priv_key_ca_cert,
                 keep_alive,
                 logger,
                 # Callback handlers
                 on_message=NOOP,
                 on_connect=NOOP,
                 on_disconnect=NOOP,
                 ):  # sad face now that we're done with arguments
        self._gcp_project_id = gcp_project_id
        self._gcp_region = gcp_region
        self._gcp_registry = gcp_registry
        self._device_id = device_id
        with open(priv_key_file, 'r') as f:
            self._private_key = f.read()
        self._priv_key_ca_cert = priv_key_ca_cert
        # a keep_alive lower than the default of 60 seconds allows for a
        # quicker disconnect detection and potential faster synchronization
        # with google data that could've changed in the meantime
        self._keep_alive = keep_alive

        self._on_message = on_message
        self._on_connect = on_connect
        self._on_disconnect = on_disconnect
        # keep track of a disconnect event occurrence
        self._disconnection_occurred = False

        self._logger = logger

        self._client = self._get_client()

    def connect(self):
        # Connect to the Google MQTT bridge.
        self._logger.info("Connecting to bridge")
        self._client.connect('mqtt.googleapis.com', 8883,
                             keepalive=self._keep_alive)
        self._client.loop_start()

    def disconnect(self):
        self._logger.info("Disconnecting from bridge")
        self._client.loop_stop()
        self._client.disconnect()

    def _create_jwt(self):
        """Creates a JWT to establish an MQTT connection. """
        token = {
            'iat': datetime.datetime.utcnow(),
            'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=60),
            # The audience field should always be set to the GCP project id.
            'aud': self._gcp_project_id
        }

        return jwt.encode(token, self._private_key, algorithm='RS256')

    def error_str(self, rc):
        """Convert a Paho error to a human readable string."""
        return '{}: {}'.format(rc, mqtt.error_string(rc))

    def on_publish(self, unused_client, unused_userdata, unused_mid):
        """Paho callback when a message is sent to the broker."""
        self._logger.debug("Received publish event")

    def on_connect(self, unused_client, unused_userdata, unused_flags, rc):
        """Callback for when a device connects."""
        self._logger.info("Handling connect message, rc: {}".format(rc))
        if rc != 0:
            self._logger.error(
                "Error connecting: {}".format(self.error_str(rc)))
        else:
            self._on_connect()
        if self._disconnection_occurred:
            # under normal functioning one would expect that the reconnect event
            # ensures that the connection is back to normal, however, that is
            # not the case since no more configuration change events from
            # google iot-core are received afterwards when modifying the
            # configuration, so restoring the client connection fully is the
            # only known way to make it work again so far.

            # confusingly enough paho loop needs to be stopped
            # as part of the restart
            self._client.loop_stop()

            # re-establish a brand new client connection
            self._client = self._get_client()
            self.connect()

            # clear flag once conditions are restored
            self._disconnection_occurred = False

    def on_disconnect(self, unused_client, unused_userdata, rc):
        """Paho callback for when a device disconnects."""
        self._logger.info("Handling disconnect message, rc: {}".format(rc))
        if rc != 0:
            self._logger.error(
                "Disconnect due to error: {}".format(self.error_str(rc)))
        # keep track of disconnection event
        self._disconnection_occurred = True
        self._on_disconnect()

    def on_message(self, client, user_data, message):
        """Callback when the device receives a message on a subscription."""

        self._logger.info("Received message from MQTT on topic: {}".format(
            message.topic))
        self._logger.debug("Message contents: {}".format(message.payload))
        try:
            # call subscriber with received data
            self._on_message(client, user_data, message.payload)
        except Exception:
            self._logger.exception(
                "Uncaught exception in on_message callback")

    def publish(self, payload, topic):
        """ Command to publish the payload on a given topic """
        self._client.publish(self._get_topic(topic), str(payload), qos=1)

    def _get_client(self):
        """ Get an MQTT Client that is connected to IoT Core """
        # /projects/PROJ/locations/LOC/registries/REG/devices/DEVICE
        client = mqtt.Client(client_id='/'.join([
            'projects', self._gcp_project_id,
            'locations', self._gcp_region,
            'registries', self._gcp_registry,
            'devices', self._device_id]))

        # With Google Cloud IoT Core, the username field is ignored, and the
        # password field is used to transmit a JWT to authorize the device.
        client.username_pw_set(username='unused', password=self._create_jwt())

        # Enable SSL/TLS support.
        client.tls_set(
            ca_certs=self._priv_key_ca_cert,
            tls_version=ssl.PROTOCOL_TLSv1_2)

        # Register message callbacks.
        client.on_publish = self.on_publish
        client.on_connect = self.on_connect
        client.on_disconnect = self.on_disconnect
        client.on_message = self.on_message

        return client

    def _get_topic(self, user_topic):
        return "/devices/{}/{}".format(self._device_id, user_topic)
