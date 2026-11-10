# DocuSense AI — Technical Configuration Conflict Test Catalogue

**Version:** 1.0  
**Purpose:** Validate extraction and review of technical limits, configuration values, and firmware specifications.  
**Test style:** Synthetic fixtures; no vendor documentation or production configuration is included.

## Interpretation rules

1. Compare like attributes first. A polling interval is not the same attribute as a gateway timeout.
2. Normalize compatible units before comparison (e.g., 500 ms = 0.5 s).
3. Compare scope/component and operating conditions. A sensor limit and a cloud-service limit may interact without being a direct contradiction.
4. Respect effective dates and firmware versions. A newer firmware value may supersede an older one rather than conflict with it.
5. Emit evidence, document provenance, severity, and a `needs_review` status. Do not silently resolve conflicts.
6. Cross-attribute compatibility checks are labelled `potential_operational_conflict`, not `direct_conflict`.

## Test cases

| ID | Source A | Source B | Expected classification | Expected dashboard behaviour |
|---|---|---|---|---|
| TC-01 | IoT sensor manual: `Sensor request timeout is 60 seconds.` | Cloud gateway spec: `Gateway request timeout limit is 30 seconds.` | Potential cross-component operational conflict; not same-attribute direct conflict unless both govern the same request timeout scope | Medium severity review card with both evidence excerpts |
| TC-02 | Sensor manual: `Polling interval is 60 seconds.` | Gateway spec: `Gateway timeout limit is 30 seconds.` | Potential operational conflict only; distinct settings | Medium severity risk card; explanation asks whether timeout applies to each poll request |
| TC-03 | Device spec: `Request timeout is 60 seconds.` | Firmware release notes: `Request timeout is 30 seconds.` | Direct conflict if scope and effective period overlap | High severity direct-conflict card |
| TC-04 | Firmware v1.2: `Retry interval is 5 seconds.` | Firmware v1.3, effective later: `Retry interval is 10 seconds.` | Versioned change; should be treated as supersession once temporal/version resolver is enabled | No active conflict; show history/change note |
| TC-05 | Sensor A: `Maximum operating temperature is 70 C.` | Gateway: `Maximum operating temperature is 55 C.` | Different component scopes; no direct conflict | No conflict card unless system requirement says both values apply to same assembly/environment |
| TC-06 | Device config: `Maximum payload size is 1 MB.` | Cloud API config: `Maximum payload size is 512 KB.` | Potential integration constraint across components | Review card; normalize size units before determining payload compatibility |
| TC-07 | Hardware manual: `Supply voltage is 5 V.` | Firmware config: `Supply voltage is 5 V.` | Consistent duplicate | No conflict card |
| TC-08 | Hardware manual: `Supply voltage is 5 V.` | Firmware config: `Supply voltage is 12 V.` | Direct conflict only if same device/board revision and conditions | High severity; evidence from both sources |
| TC-09 | Device: `Maximum retries is 3.` | Cloud client: `Maximum retries is 5.` | Scope-specific; not a direct conflict when settings belong to different components | No direct conflict; retain both EAVs |
| TC-10 | Device: `Minimum operating temperature is -10 C.` | Device: `Maximum operating temperature is 60 C.` | Compatible range | No conflict; optionally validate range bounds |
| TC-11 | Device: `Maximum operating temperature is 60 C.` | Same device: `Minimum operating temperature is 75 C.` | Invalid/empty operating range | High severity configuration-range error |
| TC-12 | Firmware spec: `Firmware version is 2.4.1.` | Manual: `Firmware version is 2.4.1.` | Consistent version | No conflict |

## Acceptance criteria

- Every extracted EAV contains `statement_id`, `document_id`, `source_file`, `line`, `entity`, `attribute`, `value`, `unit`, `scope`, `condition`, `effective_from`, `effective_to`, and exact `evidence`.
- Unit-normalized durations are represented in seconds.
- A direct conflict is only emitted for different values of the same attribute from different documents with compatible scope and unit.
- The 60-second polling / 30-second gateway timeout case is not mislabeled as a direct contradiction.
- Each finding includes its type, severity, evidence, document names, explanation, and `needs_review` status.
- The upload response includes a dashboard summary and the dashboard endpoint returns registered cards/findings.

## Current implementation boundary

The parser currently implements deterministic regex rules for common duration, retry, firmware version, temperature, payload-size, and voltage statements. Scope and time handling are intentionally conservative. TC-04 temporal supersession, TC-06 cross-unit size normalization, TC-11 range validation, and advanced component identity resolution are documented future extensions; do not claim they are fully automated in this MVP.
