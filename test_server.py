import os, unittest, threading, http.client, json
from unittest.mock import patch
from http.server import ThreadingHTTPServer
import server

class SiteTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.http=ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
        cls.thread=threading.Thread(target=cls.http.serve_forever,daemon=True)
        cls.thread.start()
        cls.env=patch.dict(os.environ,dict(SITE_ORIGIN='https://rec.example.test',SMTP_HOST='smtp.example.test',SMTP_PORT='587',SMTP_USER='sender@example.test',SMTP_PASSWORD='test-only',MAIL_FROM='sender@example.test',MAIL_TO='contact@example.test'))
        cls.env.start()
    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown();cls.http.server_close();cls.env.stop()
    def call(self,method,path,data=None,origin='https://rec.example.test'):
        c=http.client.HTTPConnection('127.0.0.1',self.http.server_port,timeout=5)
        body=json.dumps(data).encode() if data is not None else None
        c.request(method,path,body,{'Content-Type':'application/json','Origin':origin})
        r=c.getresponse();result=(r.status,r.read());c.close();return result
    def valid(self):
        return dict(nom='Recette',entreprise='Test',email='client@example.test',telephone='',service='SIG & cartographie',type='Collectivité',lieu='Paris',delai='Urgent',projet='Test isolé',website='')
    def test_pages(self):
        for p in ('/','/detection.html','/georeferencement.html','/cartographie.html','/informations.html','/healthz','/portal.js','/premium.css','/fonts/noto-display-regular.woff','/images/geovision-brand.webp'):
            self.assertEqual(self.call('GET',p)[0],200,p)
        self.assertNotIn(b'Espace client',self.call('GET','/portal.js')[1])
        for p in ('/espace.html','/api/requests','/.env','/fonts/../server.py'):
            self.assertEqual(self.call('GET',p)[0],404,p)
    def test_message(self):
        with patch.object(server,'deliver',return_value=True) as send:
            status,body=self.call('POST','/api/contact',self.valid())
            self.assertEqual(status,200);self.assertTrue(json.loads(body)['reference'].startswith('GV-'));self.assertTrue(json.loads(body)['acknowledgement_sent']);send.assert_called_once()
    def test_ack_failure_does_not_retry_request(self):
        with patch.object(server,'deliver',return_value=False):
            status,body=self.call('POST','/api/contact',self.valid())
            self.assertEqual(status,200)
            self.assertFalse(json.loads(body)['acknowledgement_sent'])
    def test_validation(self):
        for data in ({**self.valid(),'email':'x'}, {**self.valid(),'website':'bot'}, {**self.valid(),'entreprise':'a\nb'}, {**self.valid(),'projet':'x'*4001}):
            self.assertEqual(self.call('POST','/api/contact',data)[0],400)
        self.assertEqual(self.call('POST','/api/contact',self.valid(),origin='https://evil.test')[0],403)
    def test_mail_failure(self):
        with patch.object(server,'deliver',side_effect=OSError('test')):
            self.assertEqual(self.call('POST','/api/contact',self.valid())[0],502)
    def test_missing_configuration(self):
        with patch.dict(os.environ,{'MAIL_TO':''}):
            self.assertEqual(self.call('POST','/api/contact',self.valid())[0],503)
    def test_smtp_tls(self):
        with patch.object(server.smtplib,'SMTP') as smtp:
            c=smtp.return_value.__enter__.return_value
            c.send_message.return_value={}
            server.deliver(self.valid(),server.configuration(),'GV-TEST')
            c.starttls.assert_called_once();c.login.assert_called_once()
            self.assertEqual(c.send_message.call_count,2)
            msg=c.send_message.call_args_list[0].args[0]
            self.assertEqual(msg['To'],'contact@example.test')
            self.assertEqual(msg['Reply-To'],'client@example.test')
            ack=c.send_message.call_args_list[1].args[0]
            self.assertEqual(ack['To'],'client@example.test')
            self.assertEqual(ack['Reply-To'],'contact@example.test')
            self.assertIn('SIG & cartographie',ack.get_body(preferencelist=('plain',)).get_content())
            self.assertIn('GV-TEST',ack.get_body(preferencelist=('html',)).get_content())
            self.assertEqual(c.send_message.call_args_list[1].kwargs['to_addrs'],['client@example.test'])
    def test_ack_smtp_failure(self):
        with patch.object(server.smtplib,'SMTP') as smtp:
            c=smtp.return_value.__enter__.return_value
            c.send_message.side_effect=[{},OSError('test')]
            self.assertFalse(server.deliver(self.valid(),server.configuration(),'GV-TEST'))
    def test_rate_limit(self):
        with patch.object(server,'admit',return_value=False):
            self.assertEqual(self.call('POST','/api/contact',self.valid())[0],429)

if __name__=='__main__':
    unittest.main()
