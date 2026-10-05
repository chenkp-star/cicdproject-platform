import importlib.util
import io
import json
import os
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('notify', 'scripts/notify-feishu.py')
notify = importlib.util.module_from_spec(spec)
spec.loader.exec_module(notify)


class NotificationTests(unittest.TestCase):
    def test_mock_never_sends_or_needs_credentials(self):
        with patch.dict(os.environ, {}, clear=True), patch('sys.argv', ['notify', '--mock']), patch.object(notify, 'urlopen') as send, redirect_stdout(io.StringIO()):
            notify.main()
            send.assert_not_called()

    def test_signed_request_checks_business_response(self):
        env = {'FEISHU_WEBHOOK': 'https://open.feishu.cn/open-apis/bot/v2/hook/DEMO', 'FEISHU_SECRET': 'FAKE', 'BUILD_NUMBER': '7'}
        with patch.dict(os.environ, env, clear=True), patch('sys.argv', ['notify']), patch.object(notify, 'urlopen') as send, redirect_stdout(io.StringIO()):
            send.return_value.__enter__.return_value = io.StringIO('{"code":0}')
            notify.main()
            data = json.loads(send.call_args.args[0].data)
            self.assertEqual(data['sign'], notify.signature(data['timestamp'], 'FAKE'))
            self.assertIn('#7', data['content']['text'])
            send.return_value.__enter__.return_value = io.StringIO('{"code":19021}')
            with self.assertRaises(ValueError):
                notify.main()


if __name__ == '__main__':
    unittest.main()
