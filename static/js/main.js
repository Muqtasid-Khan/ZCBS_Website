(function () {
  "use strict";
  document.documentElement.classList.remove("no-js");
  var nav = document.querySelector(".site-nav");
  if (nav) {
    var onScroll = function () { nav.classList.toggle("scrolled", window.scrollY > 40); };
    onScroll(); window.addEventListener("scroll", onScroll, {passive: true});
  }
  // scroll reveal
  var els = document.querySelectorAll(".reveal");
  if ("IntersectionObserver" in window) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) { if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); } });
    }, {threshold: .12});
    els.forEach(function (el) { io.observe(el); });
  } else { els.forEach(function (el) { el.classList.add("in"); }); }

  // copy link buttons
  document.querySelectorAll("[data-copy]").forEach(function (b) {
    b.addEventListener("click", function () {
      var url = b.getAttribute("data-copy") || location.href;
      (navigator.clipboard ? navigator.clipboard.writeText(url) : Promise.reject()).then(function () {
        b.title = "Link copied"; b.innerHTML = '<i class="bi bi-check2"></i>';
      }).catch(function () { window.prompt("Copy this link:", url); });
    });
  });

  // lightbox
  var items = Array.prototype.slice.call(document.querySelectorAll("[data-lightbox]"));
  if (items.length) {
    var lb = document.createElement("div");
    lb.className = "lb"; lb.setAttribute("role", "dialog"); lb.setAttribute("aria-modal", "true"); lb.setAttribute("aria-label", "Photo viewer");
    lb.innerHTML = '<span class="count"></span><button class="fs" aria-label="Full screen"><i class="bi bi-arrows-fullscreen"></i></button>' +
      '<button class="x" aria-label="Close"><i class="bi bi-x-lg"></i></button><button class="pv" aria-label="Previous"><i class="bi bi-chevron-left"></i></button>' +
      '<img alt=""><div class="cap"></div><button class="nx" aria-label="Next"><i class="bi bi-chevron-right"></i></button>';
    document.body.appendChild(lb);
    var img = lb.querySelector("img"), cap = lb.querySelector(".cap"), count = lb.querySelector(".count"), idx = 0, last = null;
    function show(i) {
      idx = (i + items.length) % items.length;
      img.src = items[idx].getAttribute("href"); img.alt = items[idx].getAttribute("data-caption") || "";
      cap.textContent = items[idx].getAttribute("data-caption") || ""; count.textContent = (idx + 1) + " / " + items.length;
    }
    function open(i) { last = document.activeElement; show(i); lb.classList.add("open"); document.body.style.overflow = "hidden"; lb.querySelector(".x").focus(); }
    function close() { lb.classList.remove("open"); document.body.style.overflow = ""; if (document.fullscreenElement) document.exitFullscreen(); if (last) last.focus(); }
    items.forEach(function (a, i) { a.addEventListener("click", function (e) { e.preventDefault(); open(i); }); });
    lb.querySelector(".x").onclick = close;
    lb.querySelector(".pv").onclick = function () { show(idx - 1); };
    lb.querySelector(".nx").onclick = function () { show(idx + 1); };
    lb.querySelector(".fs").onclick = function () { if (!document.fullscreenElement) lb.requestFullscreen && lb.requestFullscreen(); else document.exitFullscreen(); };
    lb.addEventListener("click", function (e) { if (e.target === lb) close(); });
    document.addEventListener("keydown", function (e) {
      if (!lb.classList.contains("open")) return;
      if (e.key === "Escape") close(); else if (e.key === "ArrowLeft") show(idx - 1); else if (e.key === "ArrowRight") show(idx + 1);
    });
    var sx = null;
    lb.addEventListener("touchstart", function (e) { sx = e.touches[0].clientX; }, {passive: true});
    lb.addEventListener("touchend", function (e) { if (sx === null) return; var dx = e.changedTouches[0].clientX - sx; if (Math.abs(dx) > 50) show(idx + (dx < 0 ? 1 : -1)); sx = null; });
  }
})();
