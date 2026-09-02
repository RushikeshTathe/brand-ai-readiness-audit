# Freshness / Corroboration Checks

## 1. Entity Identity

### Extracted Information
- Brand/organization name
- Domain
- Canonical URL
- Location (address, city, country)
- Contact information (phone, email)
- Logo URL
- Organization JSON-LD
- SameAs links (social media profiles)

### Severity Rules
- **Critical**: Conflicting organization names
- **High**: Missing or inconsistent contact information
- **Medium**: Missing logo or social profiles
- **Low**: Inconsistent formatting
- **Info**: Complete identity information

## 2. Cross-page Consistency

### Facts to Compare
- Organization name
- Description/tagline
- Location
- Contact information
- Product/service names
- Pricing statements
- Company-size claims
- Explicit numerical claims
- Dates

### Normalization Rules
- Remove extra whitespace
- Normalize capitalization
- Standardize punctuation
- Handle abbreviations
- Ignore minor formatting differences

### Severity Rules
- **Critical**: Conflicting prices or legal information
- **High**: Inconsistent organization name or location
- **Medium**: Inconsistent descriptions or services
- **Low**: Minor formatting differences
- **Info**: Consistent information

## 3. Freshness Signals

### Indicators to Check
- Publication dates
- Modification dates
- Old announcements (>1 year)
- Outdated pricing
- Old statistics
- Current-year references
- Contradictory dates
- Copyright years

### Severity Rules
- **High**: Outdated pricing or legal information
- **Medium**: Old announcements or statistics
- **Low**: Missing date information
- **Info**: Fresh, up-to-date content

## 4. External Corroboration

### BASE Version Limitations
- Do not crawl the entire internet
- Do not fabricate external evidence
- Mark as "not evaluated" if unavailable
- Keep architecture ready for future extension

### Future Capabilities
- Social media profile verification
- Business listing consistency
- Review platform integration
- News and press coverage
