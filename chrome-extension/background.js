/**
 * LabMatch local dev URL — match PORT in .env / run.py (default 5001).
 * Change LABMATCH_DEV_URL if you use another port.
 */
const LABMATCH_DEV_URL = "http://127.0.0.1:5001/";

chrome.action.onClicked.addListener(() => {
  chrome.tabs.create({ url: LABMATCH_DEV_URL });
});
