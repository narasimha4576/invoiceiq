   # InvoiceIQ notes

   invoice_01: OK
   invoice_02: OK
   invoice_03: OK
   invoice_04: OK (tax_amount and total are null, which is correct)
   invoice_05 (first prompt): PROBLEM - image is cut off, but the AI filled in amounts, tax_amount 111.6 and total 731.6 that are not visible (it calculated them).
   invoice_05 (stricter prompt): amounts, subtotal, tax and total are now null (good). invoice_number "INV-TS" and invoice_date "2023-1" are still partial copies - to be caught by validators in Week 2.
   invoiceiq-api Docker image: 281 MB on disk (65.8 MB compressed)
   Day 10 review results: invoice_01-03 not flagged. invoice_04 flagged (total missing). invoice_05 flagged: date "2023-1" and missing subtotal/total caught by rules; partial invoice_number "INV-TS" caught by low AI confidence. Rules and confidence catch different mistakes.