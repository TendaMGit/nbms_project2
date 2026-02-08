# Darwin Core (TDWG)

- URLs:
  - https://www.tdwg.org/standards/dwc/
  - https://dwc.tdwg.org/terms/
- Accessed: 2026-02-08

## NBMS mapping
- Taxon and voucher entities were aligned to DwC-like concepts:
  - `TaxonConcept`, `TaxonName`, `TaxonSourceRecord`, `SpecimenVoucher`.
- IAS registry uses DwC-compatible vocab fields for:
  - `establishmentMeans`
  - `degreeOfEstablishment`
  - `pathway`
- NBMS stores both code and label in IAS profile rows to keep display stable while preserving controlled vocab semantics.
