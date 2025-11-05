# Contributing to Agents at Scale Marketplace

We welcome any and all contributions to the Agents at Scale Marketplace, at whatever level you can manage. Here are a few suggestions, but you are welcome to suggest anything else that you think improves the community for us all!

## Ways to Contribute

There are quite a few ways to contribute, such as:

* **Add new marketplace items**: Contribute new services, tools, agents, or other resources to the marketplace. See the [Adding Marketplace Items](#adding-marketplace-items) section below.
* **Report bugs and security vulnerabilities**: We use [GitHub issues](https://github.com/mckinsey/agents-at-scale-marketplace/issues) to keep track of known bugs and security vulnerabilities. We keep a close eye on them and update them when we have an internal fix in progress. Before you report a new issue, do your best to ensure your problem hasn't already been reported. If it has, just leave a comment on the existing issue, rather than create a new one.
* **Propose new marketplace items or features**: If you have ideas for new items to add to the marketplace or features to improve existing ones, please open a [GitHub issue](https://github.com/mckinsey/agents-at-scale-marketplace/issues) and describe what you would like to see, why you need it, and how it should work.
* **Review pull requests**: See the [repo](https://github.com/mckinsey/agents-at-scale-marketplace) to find open pull requests and contribute a review!
* **Contribute a fix or improvement**: If you're interested in contributing fixes or improvements to existing marketplace items or documentation, first read our guidelines for contributing developers below. Once you are ready to contribute, feel free to pick one of the issues and create a PR.
* **Contribute to the documentation**: You can help us improve the [documentation](https://mckinsey.github.io/agents-at-scale-marketplace/) online. Send us feedback as a GitHub issue or start a documentation discussion on GitHub. You are also welcome to raise a PR with a bug fix or addition to the documentation.

## Code of Conduct

The Agents at Scale team pledges to foster and maintain a friendly community. We enforce a [Code of Conduct](./CODE_OF_CONDUCT.md) to ensure every contributor is welcomed and treated with respect.

## Ways of Working

**Principle 1: Team Planning and Prioritization**
- Plan tickets for current and upcoming sprints as a team
- Final prioritization decisions rest with the product manager
- When possible, break out self-contained chunks of development that a wider group of developers can work on

**Principle 2: Design Before Code**
For non-trivial changes:
- Propose design in ticket and gather team feedback
- Use RFC pull requests or spikes to share ideas
- For architectural implications, discuss with TSC (meets weekly)
- Final implementation decisions rest with technical lead

**Principle 3: Test and Validate**
Ensure contributions include appropriate tests and validation to demonstrate functionality and prevent regressions.

**Principle 4: Implementation**
- Keep development focused on ticket requirements. If additional features or ideas arise, create new tickets and track as separate work to be prioritized by the team. Link to the original ticket.
- Use PR title prefixes (`feat:`, `bug:`, `rfc:`) to ensure changelog updates, release notes generation, and semantic versioning are managed properly.
- All pull requests must use conventional commit format in their titles. This is enforced by the `validate_pr_title` workflow and is required for Automatic version determination, Changelog generation, Semantic versioning compliance
- Supported commit types:
    - `feat`: New features (triggers minor version bump)
    - `fix`: Bug fixes (triggers patch version bump)
    - `docs`: Documentation changes
    - `chore`: Maintenance tasks
    - `refactor`: Code refactoring
    - `test`: Test additions or changes
    - `ci`: CI/CD changes
    - `build`: Build system changes
    - `perf`: Performance improvements
- Breaking changes can be indicated with `!` after the type (e.g., `feat!:`) or by including `BREAKING CHANGE:` in the commit body.

**Principle 5: Releasing**
Use conventional commits and semantic versioning.

## Adding Marketplace Items

The marketplace is designed to host a variety of items including services, tools, agents, and other resources for the ARK platform. When contributing a new item:

**Repository Structure**

Organize your contribution in the appropriate directory:
- `services/` - Platform services (e.g., observability, monitoring, data processing)
- `tools/` - Reusable utilities and tools
- `agents/` - Pre-built agents and agent templates
- Other categories as they emerge

**Required Components**

Each marketplace item should include:

1. **Directory Structure**: Create a directory under the appropriate category (e.g., `services/your-service-name/`)

2. **README.md**: Comprehensive documentation including:
   - Description and purpose
   - Features and capabilities
   - Prerequisites and dependencies
   - Installation instructions
   - Configuration options
   - Usage examples
   - Troubleshooting

3. **Helm Chart** (for services): 
   - Place in `chart/` subdirectory
   - Include `Chart.yaml` with proper metadata
   - Provide `values.yaml` with sensible defaults
   - Include necessary templates

4. **DevSpace Configuration** (recommended):
   - `devspace.yaml` for local development
   - Enables hot-reload and easy testing

5. **Documentation Page**: Add a corresponding page in `docs/content/` to appear in the online documentation

**Testing Your Contribution**

Before submitting:
- Test locally using DevSpace or Helm
- Verify all documentation is accurate
- Ensure examples work as described
- Check that your item integrates properly with the ARK platform

**Language and Technology Choices**

The marketplace welcomes contributions in various languages and technologies. Choose what best suits your use case:
- **Python**: Popular for AI/ML services, data processing, and general-purpose tools
- **Go**: Excellent for high-performance services, Kubernetes operators, and system-level tools
- **JavaScript/TypeScript**: Common for web services, UIs, and Node.js tools
- **Others**: Feel free to use other languages where appropriate

The key is that your contribution should:
- Be well-documented
- Follow Kubernetes best practices (if applicable)
- Include proper Helm charts for deployment
- Integrate cleanly with the ARK platform

## Contributing to Documentation

You can help us improve the [documentation](https://mckinsey.github.io/agents-at-scale-marketplace/) online. A contribution to the docs is often the easiest way to get started contributing to the project.

The documentation is built using Next.js and MDX, located in the `docs/` directory.

**To preview docs locally:**

```bash
cd docs
npm install
npm run dev
```

Then view the documentation at `http://localhost:3000`.

**Adding Documentation for Marketplace Items:**

When adding a new marketplace item, create a corresponding MDX file in `docs/content/`:
- For services: `docs/content/services/your-service.mdx`
- For other categories: Create appropriate subdirectories as needed

Update `docs/content/_meta.js` or relevant category `_meta.js` to include your new page in the navigation.

## Guidelines for contributing developers

Note that any contributions you make will be under the Agents At Scale [license](./LICENSE).
