const editor = document.querySelector("#content");
const lineCount = document.querySelector("#line-count");

function countLines(value) {
  return value.split(/\r\n|\r|\n/).filter((line) => line.trim().length > 0).length;
}

function updateLineCount() {
  lineCount.textContent = countLines(editor.value);
}

editor.addEventListener("input", updateLineCount);
updateLineCount();
