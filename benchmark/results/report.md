# Benchmark report

Invoices scored: 66 of 66
Overall: 526/528 field checks correct (100%)

## Field accuracy (correct / total)

| field | clean_pdf | clean_png | degraded_jpg | cut_off_png | phone_photo | smudged | layout_b | all |
|---|---|---|---|---|---|---|---|---|
| vendor_name | 12/12 | 8/8 | 8/8 | 8/8 | 12/12 | 8/8 | 10/10 | 66/66 (100%) |
| gstin | 12/12 | 8/8 | 8/8 | 8/8 | 10/12 | 8/8 | 10/10 | 64/66 (97%) |
| invoice_number | 12/12 | 8/8 | 8/8 | 8/8 | 12/12 | 8/8 | 10/10 | 66/66 (100%) |
| invoice_date | 12/12 | 8/8 | 8/8 | 8/8 | 12/12 | 8/8 | 10/10 | 66/66 (100%) |
| subtotal | 12/12 | 8/8 | 8/8 | 8/8 | 12/12 | 8/8 | 10/10 | 66/66 (100%) |
| tax_amount | 12/12 | 8/8 | 8/8 | 8/8 | 12/12 | 8/8 | 10/10 | 66/66 (100%) |
| total | 12/12 | 8/8 | 8/8 | 8/8 | 12/12 | 8/8 | 10/10 | 66/66 (100%) |
| line_items | 12/12 | 8/8 | 8/8 | 8/8 | 12/12 | 8/8 | 10/10 | 66/66 (100%) |
| line item cells | 204/204 | 156/156 | 120/120 | 116/116 | 208/208 | 120/120 | 128/128 | 1052/1052 (100%) |

## Review flag

Cut-off invoices flagged for review: 16/16
Other invoices flagged for review (false alarms): 2/50
Invented values (a value given where the page shows nothing): 0/48
Wrong but NOT flagged for review (silent errors): 0 invoices

## Note

These invoices are generated: they share one layout, and the PDFs are pictures of invoices. Real invoices are messier, so real-world accuracy is likely lower.
