// @ts-check

/** @type import("../../../../frontend/src/extension-api").ExtensionModule */
export default {
  init() {
    console.log("Initialising extension FavaNl2Bql");
  },
  onExtensionPageLoad() {
    document.getElementById("nl2bql-question")?.focus();
  },
};
