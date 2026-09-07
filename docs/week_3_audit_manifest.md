# Week 3 Data Audit Manifest

**Audit date:** 2026-09-07  
**Scope:** EFA03/EFA04 curriculum rules, public-course catalogue, source records, external references, and controlled tags.

## Evidence Summary

| Dataset | Records | Audit result |
| --- | ---: | --- |
| Sources | 25 | All verified |
| Curriculum modules | 101 | Validated against the 2026 EBE handbook |
| Curriculum rules | 65 | Valid JSON and source-backed |
| External rule references | 17 | Verified and documented |
| Public courses | 24 | All verified, available, and recommendable |

The public catalogue retains three providers: Coursera, FutureLearn, and Udemy. It covers programming/data/AI, electronics/control, communications, and career skills, with both beginner and intermediate offerings. Its electronics/control coverage includes five circuit-focused courses, including DC and AC circuit analysis.

## Resolution Record

Five records that had incomplete or superseded evidence were replaced rather than recommended with uncertain evidence:

| Course ID | Replacement | Provider |
| --- | --- | --- |
| CRS005 | Control Systems: From Mathematical Modelling to PID Control | Udemy |
| CRS007 | Introduction to Computer Networking - Beginner Crash Course | Udemy |
| CRS009 | Computer Programming for Everyone | FutureLearn |
| CRS010 | How to Get Into Web Development | FutureLearn |
| CRS011 | An Introduction to Programming Using Python | FutureLearn |

Each replacement has a provider URL, access and review date, rating mean/count/scale, source verification state, and matching course-audit record. The prior superseded and incomplete pages are not retained as recommendable data.

## Controls

- `sources.csv` records source authority, locator, review date, status, and audit notes.
- `course_audit.csv` records provider availability and whether a course is recommendable.
- Validation rejects a recommendable course unless its audit record and linked source are both verified and available.
- Course interest and career tags must come from the canonical vocabulary defined by `aliases.csv`.
- Unresolved external curriculum references are validation errors, not warnings.

## Reproduction

Run the full audit and test suite from the repository root:

```powershell
py scripts/validate_database.py
py -m pytest -q
```
