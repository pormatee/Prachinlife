window.PrachinLife = window.PrachinLife || {};
window.PrachinLife.ui = window.PrachinLife.ui || {};

window.PrachinLife.ui.showElement = function (
  id
) {
  const element =
    document.getElementById(id);

  if (element) {
    element.classList.remove(
      "hidden"
    );
  }
};

window.PrachinLife.ui.hideElement = function (
  id
) {
  const element =
    document.getElementById(id);

  if (element) {
    element.classList.add(
      "hidden"
    );
  }
};

window.PrachinLife.ui.setText = function (
  id,
  value
) {
  const element =
    document.getElementById(id);

  if (element) {
    element.textContent =
      value;
  }
};
