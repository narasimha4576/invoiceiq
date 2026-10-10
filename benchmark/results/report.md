# Benchmark report

Invoices scored: 66 of 66
Overall: 526/528 field checks correct (99.6%)

## Field accuracy (correct / total)

| field | clean_pdf | clean_png | degraded_jpg | cut_off_png | phone_photo | smudged | layout_b | all |
|---|---|---|---|---|---|---|---|---|
| vendor_name | 12/12 | 8/8 | 8/8 | 8/8 | 12/12 | 8/8 | 10/10 | 66/66 (100.0%) |
| gstin | 12/12 | 8/8 | 8/8 | 8/8 | 10/12 | 8/8 | 10/10 | 64/66 (97.0%) |
| invoice_number | 12/12 | 8/8 | 8/8 | 8/8 | 12/12 | 8/8 | 10/10 | 66/66 (100.0%) |
| invoice_date | 12/12 | 8/8 | 8/8 | 8/8 | 12/12 | 8/8 | 10/10 | 66/66 (100.0%) |
| subtotal | 12/12 | 8/8 | 8/8 | 8/8 | 12/12 | 8/8 | 10/10 | 66/66 (100.0%) |
| tax_amount | 12/12 | 8/8 | 8/8 | 8/8 | 12/12 | 8/8 | 10/10 | 66/66 (100.0%) |
| total | 12/12 | 8/8 | 8/8 | 8/8 | 12/12 | 8/8 | 10/10 | 66/66 (100.0%) |
| line_items | 12/12 | 8/8 | 8/8 | 8/8 | 12/12 | 8/8 | 10/10 | 66/66 (100.0%) |
| line item cells | 204/204 | 156/156 | 120/120 | 116/116 | 208/208 | 120/120 | 128/128 | 1052/1052 (100.0%) |

## Review flag

Incomplete invoices (cut-off or smudged) flagged for review: 16/16
Complete invoices with a wrong field, flagged for review (good catches): 2/2
Complete invoices with every field right, flagged anyway (false alarms): 0/48
Invented values (a value given where the page shows nothing): 0/48
Wrong but NOT flagged for review (silent errors): 0 invoices

## All wrong fields (first 30)

- inv_041.jpg (phone_photo, flagged): gstin expected '19DKTBD0928D6Z1', got '190KTBD0928D6Z1'
- inv_046.jpg (phone_photo, flagged): gstin expected '27ZDYEW5242O4Z6', got '27ZDYEW524204Z6'

## Note

These invoices are generated, and the PDFs are pictures of invoices. Real invoices are messier, so real-world accuracy is likely lower.
