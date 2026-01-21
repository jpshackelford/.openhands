---
name: design-doc
description: Provides guidance and templates for writing comprehensive technical design documents. Use when creating design docs, technical specifications, or architecture documents.
triggers:
  - design document
  - design doc
  - technical design
  - design template
  - write design
  - create design document
---

# Design Document Guidance

This skill provides guidance and templates for writing comprehensive design documents following established best practices.

## Purpose

This skill helps developers create well-structured design documents by providing:

1. A standardized template for design documents
2. Guidance on what to include in each section
3. Best practices for technical documentation
4. Examples of effective design document structure

## Design Document Template

The complete design document template is available at `.openhands/templates/design-document-template.md` and includes the following sections:

### 1. Introduction
- **Problem Statement**: Clearly articulate the problem and its impact using factual, non-hyperbolic language
- **Proposed Solution**: Describe the solution starting with user benefits and working toward technical implementation

### 2. User Interface / New Concepts (Optional)
- For user-facing features: Describe specific user scenarios and interaction flows
- For internal changes: Explain new or significantly altered system concepts
- Include CLI examples with commands, flags, and arguments where applicable

### 3. Other Context (Optional)
- Background information on new technologies or techniques
- Third-party library or API usage guidance
- Links to additional resources for further exploration

### 4. Technical Design
- Start with fundamental concepts and build complexity incrementally
- Use numbered subsections (4.1, 4.1.1, etc.)
- Include code examples, diagrams, and output samples
- Always specify language for code blocks, even for plaintext

### 5. Implementation Plan
- Break down work into reviewable milestones
- Include acceptance criteria (lints, tests, etc.)
- Organize iteratively: foundational → simple functionality → enhanced features
- Specify file paths for implementations and tests
- Describe what can be demoed at each milestone

## Usage Guidelines

When creating a design document:

1. **Start with the template**: Copy `.openhands/templates/design-document-template.md` as your starting point
2. **Be concise but complete**: Provide enough detail for implementation without unnecessary verbosity
3. **Think incrementally**: Structure implementation to deliver value early and build upon it
4. **Include examples**: Use code samples, CLI examples, and diagrams to illustrate concepts
5. **Consider your audience**: Write for the implementer who needs to understand and build the solution

## Template Access

```bash
# Copy the template to start a new design document
cp .openhands/templates/design-document-template.md path/to/your-design-doc.md

# Or view the template content
cat .openhands/templates/design-document-template.md
```

## Best Practices

- **Problem-first approach**: Always start by clearly defining the problem before jumping to solutions
- **User-centric language**: Describe benefits from the user's perspective before diving into technical details
- **Iterative planning**: Structure implementation to allow for early feedback and course correction
- **Concrete examples**: Use specific scenarios and code examples rather than abstract descriptions
- **Milestone-driven**: Break work into discrete, reviewable chunks that each deliver demonstrable value

## Common Pitfalls to Avoid

- Overly technical language in problem statements
- Jumping to implementation details without explaining the "why"
- Creating monolithic implementation plans without clear milestones
- Missing acceptance criteria or testing considerations
- Forgetting to specify file paths and concrete deliverables
