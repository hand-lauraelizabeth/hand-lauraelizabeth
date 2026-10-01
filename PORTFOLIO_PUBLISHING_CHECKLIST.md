# Public Portfolio Publishing Checklist

Use this checklist before moving any file from Google Drive or a work folder into GitHub or WordPress.

## Source and rights

- Confirm the file is mine to publish, or that publication is permitted by the owner/license.
- Do not publish employer, client, student, member, applicant, or participant source files unless they are already public and permission is clear.
- Prefer synthetic or public-domain replacements for professional datasets.

## Privacy and confidential information

- Remove names, emails, phone numbers, addresses, IDs, account numbers, internal URLs, meeting links, comments, reviewer identities, and other unnecessary personal or organizational information.
- Check hidden spreadsheet rows/columns/sheets, speaker notes, slide comments, tracked changes, document comments, revision history, and embedded file attachments.
- Check formulas, named ranges, pivot caches, workbook connections, document properties, EXIF/IPTC metadata, and exported filenames.

## Drive

- Keep the working/source file private.
- Do not use a private working-file Drive URL as a public portfolio link.
- Create a dedicated sanitized export or public copy when a public artifact is needed.
- Re-check the sanitized copy before changing any sharing permission.

## GitHub

- Never commit credentials, tokens, private keys, `.env` files, private Drive URLs, or confidential raw exports.
- Put non-public working material only in ignored private directories.
- Run a final repository search for names, emails, organization-specific identifiers, and common secret markers before publishing.
- Remember that deleting a file from the latest commit does not remove it from Git history.

## WordPress

- Treat anything uploaded to the WordPress media library as publicly retrievable if its URL is known or indexed.
- Upload only the sanitized public copy, never the private Drive working file.
- Prefer a portfolio case study or redacted excerpt over a full employer-owned artifact when the full file is not necessary.
- After publication, test the page in a signed-out/private browser and search for accidental direct-download URLs.

## Final check

A public artifact should remain safe if its URL is copied, indexed by a search engine, downloaded, mirrored, and viewed without authentication.
