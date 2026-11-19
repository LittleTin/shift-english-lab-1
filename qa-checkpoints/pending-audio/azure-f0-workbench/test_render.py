import io, unittest, wave
from render import prepare, speech, validate_pcm
def clip(frames=1024):
    b=io.BytesIO()
    with wave.open(b,'wb') as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(24000);w.writeframes(bytes(2*frames))
    return b.getvalue()
a={'voice':'en-US-JennyNeural','locale':'en-US','text':'A&B <C>'}
class RenderTests(unittest.TestCase):
    def test_pcm_complete(self):
        self.assertEqual(validate_pcm(clip()),1024)
    def test_truncated_body(self):
        with self.assertRaises(ValueError):
            validate_pcm(clip()[:-2])
    def test_sample_count_also_checked(self):
        b=bytearray(clip());b[40:44]=(9122).to_bytes(4,'little')
        with self.assertRaises(ValueError):
            validate_pcm(b)
    def test_escape_and_voice(self):
        self.assertIn('A&amp;B &lt;C&gt;',speech(a))
        with self.assertRaises(ValueError):
            speech({**a,'locale':'en-GB'})
    def test_options(self):
        valid=speech({**a,'text':'A. First. B. Second. C. Third.','optionCount':3})
        self.assertEqual(valid.count('interpret-as="characters"'),3)
        with self.assertRaises(ValueError):
            speech({**a,'text':'A. First. C. Second. B. Third.','optionCount':3})
    def test_bounded_pause_at_original_punctuation(self):
        t={**a,'text':'A. First. B. Second. C. Actually, Elena will be taking my place.','optionCount':3,
           'exactPauseAfter':{'phrase':'Actually,','ms':185}}
        a1=speech(t)
        self.assertIn('Actually,<break time="185ms"/> Elena', a1)
        with self.assertRaises(ValueError):
            speech({**t,'exactPauseAfter':{'phrase':'Elena','ms':185}})
        with self.assertRaises(ValueError):
            speech({**t,'exactPauseAfter':{'phrase':'Actually,','ms':900}})
    def test_plan_guard(self):
        p={'status':'editorial-ready-f0-candidate','items':[{'name':'safe-name','turns':[a]}]}
        self.assertEqual(len(prepare(p)),1)
        with self.assertRaises(ValueError):
            prepare({**p,'status':'draft'})
        with self.assertRaises(ValueError):
            prepare({**p,'items':[{'name':'../../unsafe','turns':[a]}]})
if __name__=='__main__':
    unittest.main()
