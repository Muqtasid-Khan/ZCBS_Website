/* Cinematic intro: ~5 seconds, skippable, respects reduced motion, plays once per visitor if enabled.
   The only thing remembered is a flag in the visitor's own browser (localStorage); nothing is sent anywhere. */
(function () {
  "use strict";
  var intro = document.getElementById("intro");
  if (!intro) return;
  var once = intro.getAttribute("data-once") === "1";
  var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var seen = false;
  try { seen = localStorage.getItem("zcbs_intro_seen") === "1"; } catch (e) {}
  function finishNow() { document.documentElement.classList.add("no-intro"); document.body.classList.add("intro-done"); document.body.classList.remove("intro-active"); }
  if (reduce || (once && seen)) { finishNow(); return; }

  document.body.classList.add("intro-active");
  var canvas = intro.querySelector("canvas"), ctx = canvas.getContext("2d"), W, H, raf, t0 = performance.now(), done = false, parts = [];
  function size() { W = canvas.width = window.innerWidth; H = canvas.height = window.innerHeight; }
  size(); window.addEventListener("resize", size);
  for (var i = 0; i < 70; i++) parts.push({x: Math.random(), y: Math.random(), s: Math.random() * 1.4 + .3, v: Math.random() * .00008 + .00002});
  function draw(now) {
    var t = (now - t0) / 1000; ctx.clearRect(0, 0, W, H);
    // architectural arch lines drawing in
    var cx = W / 2, base = H * .86, aw = Math.min(W * .34, 330), prog = Math.min(1, t / 2.6);
    ctx.strokeStyle = "rgba(201,162,75," + (.18 + .25 * prog) + ")"; ctx.lineWidth = 1;
    for (var k = 0; k < 4; k++) {
      var w = aw * (1 + k * .38), h = w * 1.05, p = Math.max(0, Math.min(1, prog * 1.4 - k * .18));
      ctx.beginPath(); ctx.moveTo(cx - w, base);
      var total = h * 2 + Math.PI * w, run = total * p, seg;
      seg = Math.min(run, h); ctx.lineTo(cx - w, base - seg); run -= seg;
      if (run > 0) { var ang = Math.min(Math.PI, run / w); ctx.arc(cx, base - h, w, Math.PI, Math.PI + ang); run -= ang * w; }
      if (run > 0) { ctx.moveTo(cx + w, base - h); ctx.lineTo(cx + w, base - h + Math.min(run, h)); }
      ctx.stroke();
    }
    // drifting particles
    ctx.fillStyle = "rgba(230,210,154,.55)";
    parts.forEach(function (p) { p.y -= p.v * 16; if (p.y < 0) p.y = 1; ctx.globalAlpha = .25 + .5 * Math.abs(Math.sin(t + p.x * 9)); ctx.beginPath(); ctx.arc(p.x * W, p.y * H, p.s, 0, 6.283); ctx.fill(); });
    ctx.globalAlpha = 1;
    if (!done) raf = requestAnimationFrame(draw);
  }
  raf = requestAnimationFrame(draw);

  var code = intro.querySelector(".intro-code"), lines = [
    ['<span class="k">import</span> integrity, leadership', 0],
    ['character.<span class="k">build</span>()  <span class="ok">// ready</span>', 0]];
  var li = 0, ci = 0, html = "";
  function type() {
    if (done) return;
    var raw = lines[li][0].replace(/<[^>]+>/g, ""), full = lines[li][0];
    // type by revealing characters of the visible text while keeping tags intact
    var out = "", vis = 0, inTag = false;
    for (var j = 0; j < full.length && vis <= ci; j++) { var c = full[j]; out += c; if (c === "<") inTag = true; else if (c === ">") inTag = false; else if (!inTag) vis++; }
    code.innerHTML = html + out + '<span class="caret"></span>';
    if (ci < raw.length) { ci++; setTimeout(type, 28); }
    else { html += full + "<br>"; li++; ci = 0; if (li < lines.length) setTimeout(type, 260); else code.innerHTML = html + '<span class="caret"></span>'; }
  }
  setTimeout(type, 500);
  var t1 = setTimeout(function () { intro.classList.add("show-logo"); }, 2500);
  var t2 = setTimeout(leave, 4800);
  function leave() {
    if (done) return; done = true; clearTimeout(t1); clearTimeout(t2); cancelAnimationFrame(raf);
    try { localStorage.setItem("zcbs_intro_seen", "1"); } catch (e) {}
    intro.classList.add("leaving"); document.body.classList.add("intro-done"); document.body.classList.remove("intro-active");
    setTimeout(function () { intro.remove(); document.documentElement.classList.add("no-intro"); }, 1050);
  }
  intro.querySelector(".intro-skip").addEventListener("click", leave);
  document.addEventListener("keydown", function (e) { if (e.key === "Escape") leave(); });
})();
