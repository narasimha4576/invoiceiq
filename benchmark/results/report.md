# Benchmark report

Invoices scored: 36 of 36
Overall: 288/288 field checks correct (100%)

## Field accuracy (correct / total)

| field | clean_pdf | clean_png | degraded_jpg | cut_off_png | all |
|---|---|---|---|---|---|
| vendor_name | 12/12 | 8/8 | 8/8 | 8/8 | 36/36 (100%) |
| gstin | 12/12 | 8/8 | 8/8 | 8/8 | 36/36 (100%) |
| invoice_number | 12/12 | 8/8 | 8/8 | 8/8 | 36/36 (100%) |
| invoice_date | 12/12 | 8/8 | 8/8 | 8/8 | 36/36 (100%) |
| subtotal | 12/12 | 8/8 | 8/8 | 8/8 | 36/36 (100%) |
| tax_amount | 12/12 | 8/8 | 8/8 | 8/8 | 36/36 (100%) |
| total | 12/12 | 8/8 | 8/8 | 8/8 | 36/36 (100%) |
| line_items | 12/12 | 8/8 | 8/8 | 8/8 | 36/36 (100%) |
| line item cells | 204/204 | 156/156 | 120/120 | 116/116 | 596/596 (100%) |

## Review flag

Cut-off invoices flagged for review: 8/8
Other invoices flagged for review (false alarms): 0/28
Invented values (a value given where the page shows nothing): 0/24
Wrong but NOT flagged for review (silent errors): 0 invoices

## Note

These invoices are generated: they share one layout, and the PDFs are pictures of invoices. Real invoices are messier, so real-world accuracy is likely lower.
