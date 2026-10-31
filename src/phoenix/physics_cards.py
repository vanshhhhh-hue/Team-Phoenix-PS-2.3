"""Self-contained, keyboard-accessible 3D flip card. No external assets or requests."""
from html import escape


def flashcard_html(card):
    fields={key:escape(str(value)) for key,value in card.items()}
    template='''<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
*{box-sizing:border-box}body{margin:0;padding:8px;background:transparent;color:#303c32;font:16px/1.5 system-ui,sans-serif}
.flip{display:block;width:100%;height:365px;padding:0;border:0;background:transparent;perspective:1400px;cursor:pointer;text-align:left;color:inherit}
.flip:focus-visible{outline:3px solid #526744;outline-offset:3px;border-radius:20px}
.inner{display:block;height:100%;width:100%;position:relative;transform-style:preserve-3d;transition:transform .65s cubic-bezier(.2,.7,.3,1)}
.flip[aria-pressed=true] .inner{transform:rotateY(180deg)}
.face{position:absolute;inset:0;display:flex;flex-direction:column;justify-content:space-between;padding:30px;border-radius:20px;backface-visibility:hidden;-webkit-backface-visibility:hidden;box-shadow:0 10px 25px #313d2912;border:1px solid #71825d30;overflow:auto}
.front{background:linear-gradient(125deg,#dce6d3 0%,#e9e6cd 50%,#f2dfce 100%)}
.back{background:linear-gradient(125deg,#344d40 0%,#526b50 55%,#738261 100%);color:#fbf9ee;transform:rotateY(180deg)}
.label{font-size:11px;text-transform:uppercase;letter-spacing:.15em;font-weight:700;opacity:.8}
.prompt{font:clamp(23px,3.6vw,34px)/1.25 Georgia,serif;max-width:760px;margin:17px 0}
.answer{font:clamp(19px,2.8vw,25px)/1.4 Georgia,serif;margin:12px 0}
.memory{background:#ffffff18;border:1px solid #ffffff30;border-radius:10px;padding:12px 16px;margin:12px 0;font-size:15px}
.example{font-size:14px;line-height:1.6;opacity:.95}.instruction{font-size:12px;opacity:.8;margin-top:10px}
@media(max-width:480px){.flip{height:445px}.face{padding:23px}.prompt{font-size:26px}.answer{font-size:21px}}
@media(prefers-reduced-motion:reduce){.inner{transition:none}}
</style>
<button class="flip" id="flip" type="button" aria-label="Show answer: __PROMPT__" data-front-label="Show answer: __PROMPT__" data-back-label="Answer: __ANSWER__. Memory cue: __MNEMONIC__. Press to return to the question." aria-pressed="false">
 <span class="inner">
  <span class="face front" id="front" aria-hidden="false">
   <span class="label">__TITLE__ · __KIND__</span>
   <span class="prompt">__PROMPT__</span>
   <span class="instruction">Think it through. Click or press Enter to flip ↻</span>
  </span>
  <span class="face back" id="back" aria-hidden="true">
   <span class="label">The idea, made simple</span>
   <span class="answer">__ANSWER__</span>
   <span class="memory"><strong>Remember it this way</strong><br>__MNEMONIC__</span>
   <span class="example">__EXAMPLE__</span>
   <span class="instruction">Click or press Enter to return ↻</span>
  </span>
 </span>
</button>
<script>
const button=document.getElementById('flip');
button.addEventListener('click',()=>{
 const flipped=button.getAttribute('aria-pressed')!=='true';
 button.setAttribute('aria-pressed',String(flipped));
 button.setAttribute('aria-label',flipped ? button.dataset.backLabel : button.dataset.frontLabel);
 document.getElementById('front').setAttribute('aria-hidden',String(flipped));
 document.getElementById('back').setAttribute('aria-hidden',String(!flipped));
});
</script></html>'''
    for key in ('title','kind','prompt','answer','mnemonic','example'):
        template=template.replace('__'+key.upper()+'__',fields[key])
    return template
