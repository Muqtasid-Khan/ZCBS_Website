/* Drag rows to reorder on admin list pages that have an editable "order" column.
   After dropping, the order numbers are rewritten (10, 20, 30…); press the Save button to keep them. */
(function () {
  document.addEventListener("DOMContentLoaded", function () {
    var table = document.getElementById("result_list");
    if (!table) return;
    var inputs = table.querySelectorAll('input[name$="-order"]');
    if (!inputs.length) return;
    var body = table.tBodies[0], dragRow = null;
    var hint = document.createElement("div");
    hint.className = "zcbs-sort-hint";
    hint.textContent = "Tip: drag rows up or down to rearrange, then press Save.";
    table.parentNode.insertBefore(hint, table);
    Array.prototype.forEach.call(body.rows, function (row) {
      row.draggable = true;
      row.style.cursor = "grab";
      row.addEventListener("dragstart", function (e) { dragRow = row; row.classList.add("zcbs-dragging"); e.dataTransfer.effectAllowed = "move"; });
      row.addEventListener("dragend", function () { row.classList.remove("zcbs-dragging"); Array.prototype.forEach.call(body.rows, function (r) { r.classList.remove("zcbs-over"); }); });
      row.addEventListener("dragover", function (e) { e.preventDefault(); row.classList.add("zcbs-over"); });
      row.addEventListener("dragleave", function () { row.classList.remove("zcbs-over"); });
      row.addEventListener("drop", function (e) {
        e.preventDefault();
        if (!dragRow || dragRow === row) return;
        var rows = Array.prototype.slice.call(body.rows);
        if (rows.indexOf(dragRow) < rows.indexOf(row)) row.after(dragRow); else row.before(dragRow);
        Array.prototype.forEach.call(body.rows, function (r, i) {
          var inp = r.querySelector('input[name$="-order"]');
          if (inp) { inp.value = (i + 1) * 10; inp.dispatchEvent(new Event("change", {bubbles: true})); }
        });
      });
    });
  });
})();
