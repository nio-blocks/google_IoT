from unittest.mock import patch

from nio.testing.block_test_case import NIOBlockTestCase
from nio.signal.base import Signal
from nio import Block

from ..google_iot_mqtt_base_block import GoogleIoTMQTTBase
from ..google_iot_mqtt_publish_block import GoogleIoTMQTTPublish


class TestMQTTBase(NIOBlockTestCase):

    @patch("{}.{}".format(GoogleIoTMQTTBase.__module__, 'IoTCoreClient'))
    def test_configure(self, patched_client):
        """Assert connect/disconnect calls."""

        class GoogleIoTMQTT(GoogleIoTMQTTBase, Block):
            pass

        blk = GoogleIoTMQTT()
        blk.project_id = "project_id"
        blk.registry_id = "registry_id"
        blk.device_id = "device_id"

        self.assertEqual(patched_client.call_count, 0)

        self.configure_block(blk, {})
        blk.start()
        blk.stop()
        self.assertEqual(blk._client.connect.call_count, 1)
        self.assertEqual(blk._client.disconnect.call_count, 1)
        self.assertEqual(patched_client.call_count, 1)


class TestMQTTPublish(NIOBlockTestCase):

    @patch("{}.{}".format(GoogleIoTMQTTBase.__module__, 'IoTCoreClient'))
    def test_process_signals(self, patched_client):

        blk = GoogleIoTMQTTPublish()
        blk.project_id = "project_id"
        blk.registry_id = "registry_id"
        blk.device_id = "device_id"

        self.assertEqual(patched_client.call_count, 0)
        self.configure_block(blk, {"topic": "testtopic"})
        self.assertEqual(patched_client.call_count, 1)

        blk.start()
        self.assertEqual(blk._client.publish.call_count, 0)
        blk.process_signals([Signal({"text": "hello"})])
        self.assertEqual(blk._client.publish.call_count, 1)
        blk._client.publish.assert_called_with(
            topic=blk.topic(),
            payload=blk.data_to_publish(Signal({"text": "hello"}))
        )
        blk.stop()

        self.assert_num_signals_notified(0)

        self.assertEqual(patched_client.call_count, 1)
