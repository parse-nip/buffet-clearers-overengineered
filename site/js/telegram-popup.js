/**
 * Entry + exit-intent modal for Telegram group link.
 * Uses sessionStorage so repeat refreshes in the same tab stay tolerable.
 */
(function () {
  const STORAGE_ENTRY_DISMISSED = "bc_tg_entry_dismissed";
  const STORAGE_EXIT_SHOWN = "bc_tg_exit_shown";
  const ENTRY_DELAY_MS = 750;
  const EXIT_GRACE_MS = 12000;

  const dialog = document.getElementById("tgPromo");
  if (!dialog || typeof dialog.showModal !== "function") return;

  const cta = dialog.querySelector(".tg-modal__cta");

  const loadAt = Date.now();
  let promoSource = null;

  function show(source) {
    if (dialog.open) return;
    promoSource = source;
    dialog.showModal();
    cta?.focus();
  }

  function onClose() {
    if (promoSource === "entry") {
      sessionStorage.setItem(STORAGE_ENTRY_DISMISSED, "1");
    }
    if (promoSource === "exit") {
      sessionStorage.setItem(STORAGE_EXIT_SHOWN, "1");
    }
    promoSource = null;
  }

  dialog.addEventListener("close", onClose);

  dialog.addEventListener("cancel", (e) => e.preventDefault());

  cta?.addEventListener("click", () => dialog.close());

  window.setTimeout(() => {
    if (sessionStorage.getItem(STORAGE_ENTRY_DISMISSED)) return;
    if (dialog.open) return;
    show("entry");
  }, ENTRY_DELAY_MS);

  document.addEventListener(
    "mouseout",
    (e) => {
      if (e.relatedTarget != null) return;
      if (e.clientY > 0) return;
      if (Date.now() - loadAt < EXIT_GRACE_MS) return;
      if (sessionStorage.getItem(STORAGE_EXIT_SHOWN)) return;
      if (dialog.open) return;
      show("exit");
    },
    { passive: true }
  );
})();
