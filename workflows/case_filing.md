# Case Filing Workflow

## Objective

Automate submission of a support/complaint case on an external case-filing website using browser automation.

## Required Inputs

| Input | Source | Example |
|-------|--------|---------|
| Case filing URL | `.env` → `CASE_FILING_URL` | `https://example.com/file-a-case` |
| Case fields | User form in Streamlit UI | Name, email, category, description |

## Tool Sequence

| Step | Tool | What It Does |
|------|------|-------------|
| 1 | `tools/file_case.py` | Launch Playwright browser, fill form, submit, take screenshot |
| 2 | `tools/streamlit_app.py` | Provide form UI and display results |

## Expected Outputs

- `.tmp/case_filing_screenshot.png` — confirmation screenshot
- Console output with success/failure status

## Setting Up for a New Website

When the target URL is provided:

1. Install Playwright browsers: `playwright install chromium`
2. Run the code generator: `playwright codegen <URL>`
3. Click through the form manually in the browser that opens
4. Copy the CSS selectors into the `FIELD_MAP` dict in `tools/file_case.py`
5. Set the `SUBMIT_SELECTOR` to the submit button's selector
6. Update `CASE_FILING_URL` in `.env`
7. Test: `python tools/file_case.py --case-data '{"name": "Test"}' --headed`

## Edge Cases

| Scenario | Handling |
|----------|----------|
| CASE_FILING_URL not set | User sees warning in Streamlit UI; script exits with error |
| FIELD_MAP empty | Stub mode: navigates to URL, takes screenshot, skips form filling |
| Page load timeout | Playwright raises timeout error after 30s |
| Element not found | Playwright error logged; screenshot captured of error state |
| CAPTCHA present | Manual intervention needed; run with `--headed` flag |
| Submission timeout | 15s wait for network idle after click; error if exceeded |
