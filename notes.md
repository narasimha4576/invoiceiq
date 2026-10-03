   # InvoiceIQ notes

   invoice_01: OK
   invoice_02: OK
   invoice_03: OK
   invoice_04: OK (tax_amount and total are null, which is correct)
   invoice_05 (first prompt): PROBLEM - image is cut off, but the AI filled in amounts, tax_amount 111.6 and total 731.6 that are not visible (it calculated them).
   invoice_05 (stricter prompt): amounts, subtotal, tax and total are now null (good). invoice_number "INV-TS" and invoice_date "2023-1" are still partial copies - to be caught by validators in Week 2.