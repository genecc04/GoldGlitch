function setupDirectionToggle(root) {
  const typeField = root.querySelector('#id_type');
  const directionRow = root.querySelector('#id_direction')?.closest('p');
  if (!typeField || !directionRow) return;

  function toggle() {
    directionRow.style.display = typeField.value === 'transfer' ? '' : 'none';
  }

  typeField.addEventListener('change', toggle);
  toggle();
}

document.addEventListener('DOMContentLoaded', function () {
  setupDirectionToggle(document);
});