import os, sys
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE"); os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import anthropic
from src import config as C
from src.chunkers.prompts import formatter_system_prompt, formatter_user_prompt, number_sentences
from src.chunkers.formatter import _subject_phrase
from src.textutil import sentence_spans
from src.datasets import track_b_public as TB

ds = TB.load_b2(seed=1337, new_seed=20272, n_queries=180)
doc = ds.documents[0]
spans = sentence_spans(doc.text)
sents = [doc.text[s:e] for s, e in spans]
sysp = formatter_system_prompt(True, True, True)
usr = formatter_user_prompt(_subject_phrase(doc.text, spans), number_sentences(sents))
print(f"doc sents={len(sents)} sys_tok~{len(sysp)//4} usr_tok~{len(usr)//4}")

cl = anthropic.Anthropic()
for mt in (1024, 4096):
    m = cl.messages.create(model="claude-sonnet-5", max_tokens=mt, system=sysp,
                           messages=[{"role": "user", "content": usr}])
    txt = "".join(b.text for b in m.content if getattr(b, "type", "") == "text")
    print(f"max_tokens={mt}: stop={m.stop_reason} out_tok={m.usage.output_tokens} "
          f"text_len={len(txt)} head={txt[:80]!r}")
