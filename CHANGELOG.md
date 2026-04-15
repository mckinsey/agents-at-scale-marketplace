# Changelog

## [0.1.29](https://github.com/mckinsey/agents-at-scale-marketplace/compare/v0.1.28...v0.1.29) (2026-04-15)


### Bug Fixes

* Allow release-please to update all appVersion values ([#217](https://github.com/mckinsey/agents-at-scale-marketplace/issues/217)) ([f23d8e4](https://github.com/mckinsey/agents-at-scale-marketplace/commit/f23d8e4a0ebf728a4e91287d52e1e9ec89f45323))
* company house api key fix ([#212](https://github.com/mckinsey/agents-at-scale-marketplace/issues/212)) ([c7a6aa2](https://github.com/mckinsey/agents-at-scale-marketplace/commit/c7a6aa23a454f7aed78aab596b822fea5d9aec15))

## [0.1.28](https://github.com/mckinsey/agents-at-scale-marketplace/compare/v0.1.27...v0.1.28) (2026-04-14)


### Features

* marketplace install detection and url discovery ([#196](https://github.com/mckinsey/agents-at-scale-marketplace/issues/196)) ([b016ccf](https://github.com/mckinsey/agents-at-scale-marketplace/commit/b016ccf3203d5895ff7e70b40d349a66bf512bdf))
* OpenAI responses executor ([#179](https://github.com/mckinsey/agents-at-scale-marketplace/issues/179)) ([cb852e1](https://github.com/mckinsey/agents-at-scale-marketplace/commit/cb852e11420a5228993e76e4e0c95e45b0a24e5a))
* **openai-responses:** improve example agents and docs ([#211](https://github.com/mckinsey/agents-at-scale-marketplace/issues/211)) ([8826200](https://github.com/mckinsey/agents-at-scale-marketplace/commit/88262007dbe3e231a613c5e8de96af25d535c065))


### Bug Fixes

* use CPU-only PyTorch in speech-mcp-server to reduce build time ([#168](https://github.com/mckinsey/agents-at-scale-marketplace/issues/168)) ([18c30af](https://github.com/mckinsey/agents-at-scale-marketplace/commit/18c30afae7ccbe28ff34891da67729d62bdf0d78))

## [0.1.27](https://github.com/mckinsey/agents-at-scale-marketplace/compare/v0.1.26...v0.1.27) (2026-04-03)


### Bug Fixes

* **executors/claude-agent-sdk:** pin dependencies via uv.lock in Docker build ([#190](https://github.com/mckinsey/agents-at-scale-marketplace/issues/190)) ([5e130e0](https://github.com/mckinsey/agents-at-scale-marketplace/commit/5e130e0235ea5553a42c973a58d11a9c8795a170))

## [0.1.26](https://github.com/mckinsey/agents-at-scale-marketplace/compare/v0.1.25...v0.1.26) (2026-04-02)


### Bug Fixes

* **executors/claude-agent-sdk:** update model reference to claude-sonnet-4-6 ([#188](https://github.com/mckinsey/agents-at-scale-marketplace/issues/188)) ([b17021b](https://github.com/mckinsey/agents-at-scale-marketplace/commit/b17021bd4379a01baafe0e20b90a5b8b5b09d66e))

## [0.1.25](https://github.com/mckinsey/agents-at-scale-marketplace/compare/v0.1.24...v0.1.25) (2026-04-02)


### Bug Fixes

* replace local file:// helm refs with OCI registry and pin ark-sdk ([#182](https://github.com/mckinsey/agents-at-scale-marketplace/issues/182)) ([0b3a907](https://github.com/mckinsey/agents-at-scale-marketplace/commit/0b3a907b6118ce0655be024b1b34474a2334b498))

## [0.1.24](https://github.com/mckinsey/agents-at-scale-marketplace/compare/v0.1.23...v0.1.24) (2026-03-30)


### Features

* **executor-claude-agent-sdk:** read model config from Model CRD ([#158](https://github.com/mckinsey/agents-at-scale-marketplace/issues/158)) ([df75acb](https://github.com/mckinsey/agents-at-scale-marketplace/commit/df75acb09ef1b57226b38fc857db0c0d566ca697))


### Bug Fixes

* **charts:** bump file-gateway dependency to 0.1.5 in demo bundles ([#151](https://github.com/mckinsey/agents-at-scale-marketplace/issues/151)) ([9859d1d](https://github.com/mckinsey/agents-at-scale-marketplace/commit/9859d1d82c9552bd6da5d3177bb0a742513dbb49))
* remove root requirement from versitygw init container ([#155](https://github.com/mckinsey/agents-at-scale-marketplace/issues/155)) ([04952cc](https://github.com/mckinsey/agents-at-scale-marketplace/commit/04952cc21587fb6e8676a50a01ccdb5d631dadce))
* resolve deployment failures for team CRDs and file-gateway dependency             ([#157](https://github.com/mckinsey/agents-at-scale-marketplace/issues/157)) ([d68bdc5](https://github.com/mckinsey/agents-at-scale-marketplace/commit/d68bdc58842314de3e877d0b58d118f38a78de78))

## [0.1.23](https://github.com/mckinsey/agents-at-scale-marketplace/compare/v0.1.22...v0.1.23) (2026-03-25)


### Features

* **executor-claude-agent-sdk:** add MCP server support ([#150](https://github.com/mckinsey/agents-at-scale-marketplace/issues/150)) ([39caf9e](https://github.com/mckinsey/agents-at-scale-marketplace/commit/39caf9e9aa25b67022d53e8d857b23955ff7a603))
* **executor-claude-agent-sdk:** add native Claude Agent SDK executor ([#146](https://github.com/mckinsey/agents-at-scale-marketplace/issues/146)) ([af4ac81](https://github.com/mckinsey/agents-at-scale-marketplace/commit/af4ac81fb6d78eda5dfafd2461c18c41ac580a8d))
* **executor-langchain:** add RBAC for query extension CRD resolution ([#136](https://github.com/mckinsey/agents-at-scale-marketplace/issues/136)) ([c9f836e](https://github.com/mckinsey/agents-at-scale-marketplace/commit/c9f836e66a37d718f920fd29516b5f18c9caa6bf))
* **executor-langchain:** conversation history management ([#138](https://github.com/mckinsey/agents-at-scale-marketplace/issues/138)) ([b7b4241](https://github.com/mckinsey/agents-at-scale-marketplace/commit/b7b42417cdeb8fc988dace57952b2c5f49a30c21))
* kyc onboarding bundle ([#123](https://github.com/mckinsey/agents-at-scale-marketplace/issues/123)) ([1470e6c](https://github.com/mckinsey/agents-at-scale-marketplace/commit/1470e6c14ebd9b28634b8b504962c5d56008248b))


### Bug Fixes

* file gateway name ([#145](https://github.com/mckinsey/agents-at-scale-marketplace/issues/145)) ([e19e994](https://github.com/mckinsey/agents-at-scale-marketplace/commit/e19e994c749ec0e21d512ca0f72fcf1a8caa4bcf))

## [0.1.22](https://github.com/mckinsey/agents-at-scale-marketplace/compare/v0.1.21...v0.1.22) (2026-03-11)


### Bug Fixes

* **charts:** update stale subchart dependency versions ([#133](https://github.com/mckinsey/agents-at-scale-marketplace/issues/133)) ([7f229d2](https://github.com/mckinsey/agents-at-scale-marketplace/commit/7f229d2e544a834b99e0cf8e7355e69b2aa7e95d))
* **executor-langchain:** downgrade Python from 3.14 to 3.12 ([#131](https://github.com/mckinsey/agents-at-scale-marketplace/issues/131)) ([ecc353c](https://github.com/mckinsey/agents-at-scale-marketplace/commit/ecc353c9fb0b97702bfa8d7023b2c751a9fe272e))

## [0.1.21](https://github.com/mckinsey/agents-at-scale-marketplace/compare/v0.1.20...v0.1.21) (2026-02-26)


### Features

* add cobol-modernization tech demo ([#115](https://github.com/mckinsey/agents-at-scale-marketplace/issues/115)) ([81197c2](https://github.com/mckinsey/agents-at-scale-marketplace/commit/81197c2dfaf6a408f038a7f949acaf3030c4834c))
* Added Namespace condition for Cobol Demo ([#121](https://github.com/mckinsey/agents-at-scale-marketplace/issues/121)) ([799d1a2](https://github.com/mckinsey/agents-at-scale-marketplace/commit/799d1a22c0a505c322d468c58f91e82e06332515))
* kyc demo bundle with agents, teams and charts ([#104](https://github.com/mckinsey/agents-at-scale-marketplace/issues/104)) ([2f7375a](https://github.com/mckinsey/agents-at-scale-marketplace/commit/2f7375a823034a300309a27d4f3c84d3255664b2))
* langchain executor service ([#124](https://github.com/mckinsey/agents-at-scale-marketplace/issues/124)) ([8594e7d](https://github.com/mckinsey/agents-at-scale-marketplace/commit/8594e7d1b52e8dd83689eb6d8d445e0cea8b6a32))
* trigger first release filesystem mcp server ([#110](https://github.com/mckinsey/agents-at-scale-marketplace/issues/110)) ([02a0f59](https://github.com/mckinsey/agents-at-scale-marketplace/commit/02a0f59fe12e15bc458c7a4d3554d009927c9de9))


### Bug Fixes

* shorten agent description for Noah ([#114](https://github.com/mckinsey/agents-at-scale-marketplace/issues/114)) ([a6bcab9](https://github.com/mckinsey/agents-at-scale-marketplace/commit/a6bcab9459a14b607b70a2ed59a70be53515e01c))
* update RBAC and service account configurations in KYC demo bundle ([#113](https://github.com/mckinsey/agents-at-scale-marketplace/issues/113)) ([f56a738](https://github.com/mckinsey/agents-at-scale-marketplace/commit/f56a73821a55d7c31646b6c38f104297dca965cf))

## [0.1.20](https://github.com/mckinsey/agents-at-scale-marketplace/compare/v0.1.19...v0.1.20) (2026-01-14)


### Features

* add a2a-inspector service ([#79](https://github.com/mckinsey/agents-at-scale-marketplace/issues/79)) ([6ef6b68](https://github.com/mckinsey/agents-at-scale-marketplace/commit/6ef6b68e18a0e16236d1441f32d443a96d4d7d46))
* Add automated release management with Release Please and refactor CI/CD workflows ([#7](https://github.com/mckinsey/agents-at-scale-marketplace/issues/7)) ([a5edde7](https://github.com/mckinsey/agents-at-scale-marketplace/commit/a5edde7f937672bc1c45115f46bec049b8e50661))
* Add chart artifact attachment to GitHub Releases ([#49](https://github.com/mckinsey/agents-at-scale-marketplace/issues/49)) ([1c3195d](https://github.com/mckinsey/agents-at-scale-marketplace/commit/1c3195d8054ffb535afbb62736460dbb0242d678))
* Add Contributors Section and Contributing Guidelines ([#8](https://github.com/mckinsey/agents-at-scale-marketplace/issues/8)) ([5138db0](https://github.com/mckinsey/agents-at-scale-marketplace/commit/5138db06bbb90d4260302ca7abf9670b3854c981))
* Add Helm NOTES.txt templates for langfuse and phoenix ([#64](https://github.com/mckinsey/agents-at-scale-marketplace/issues/64)) ([5ad1299](https://github.com/mckinsey/agents-at-scale-marketplace/commit/5ad129904763cbcd9bfafbf68da2d2724169424c))
* add httproute crd check ([#55](https://github.com/mckinsey/agents-at-scale-marketplace/issues/55)) ([88cbcf8](https://github.com/mckinsey/agents-at-scale-marketplace/commit/88cbcf8b643ee5a42220d5edead51645ad977402))
* Add MCP Inspector service ([#68](https://github.com/mckinsey/agents-at-scale-marketplace/issues/68)) ([932bbe6](https://github.com/mckinsey/agents-at-scale-marketplace/commit/932bbe655cbc3f124132a03d530a16bde458ab02))
* add Noah runtime administration agent service ([#69](https://github.com/mckinsey/agents-at-scale-marketplace/issues/69)) ([e21b306](https://github.com/mckinsey/agents-at-scale-marketplace/commit/e21b306d2e98574c3156d9248c5eb9e888a23481))
* add workflow to validate PR titles against conventional commits ([#3](https://github.com/mckinsey/agents-at-scale-marketplace/issues/3)) ([591fdf5](https://github.com/mckinsey/agents-at-scale-marketplace/commit/591fdf5794454ec2c587f6da870f993fdce7f29a))
* Ark Sandbox ([#83](https://github.com/mckinsey/agents-at-scale-marketplace/issues/83)) ([260097d](https://github.com/mckinsey/agents-at-scale-marketplace/commit/260097dfe024ac8721e2d950c27e7bb3ae3e8f60))
* docs & phoenix migration & CI/CD ([#2](https://github.com/mckinsey/agents-at-scale-marketplace/issues/2)) ([aa62bdb](https://github.com/mckinsey/agents-at-scale-marketplace/commit/aa62bdb244cdccc51897587c6e5ff287223bd42b))
* Enhance ARK Platform Visibility ([#50](https://github.com/mckinsey/agents-at-scale-marketplace/issues/50)) ([78be24d](https://github.com/mckinsey/agents-at-scale-marketplace/commit/78be24d51f085d03d12c6d050cdceaf9ad69b1e8))
* file-gateway support ([#88](https://github.com/mckinsey/agents-at-scale-marketplace/issues/88)) ([d085164](https://github.com/mckinsey/agents-at-scale-marketplace/commit/d085164260843698ecdb0d54c86af8877217a1b9))
* langfuse docs and service migration ([#9](https://github.com/mckinsey/agents-at-scale-marketplace/issues/9)) ([8877603](https://github.com/mckinsey/agents-at-scale-marketplace/commit/8877603701d45c8369b3df7c74c16897d8037cb0))
* migrate ark marketplace following anthropic plugin marketplace ([#77](https://github.com/mckinsey/agents-at-scale-marketplace/issues/77)) ([115d3aa](https://github.com/mckinsey/agents-at-scale-marketplace/commit/115d3aa73ae13621180950769b3eeebcc3d8f2cc))
* migrate contributor list from ark ([#67](https://github.com/mckinsey/agents-at-scale-marketplace/issues/67)) ([311aa95](https://github.com/mckinsey/agents-at-scale-marketplace/commit/311aa95d7b99ed13c4214c06348aa0533763118c))
* trigger first release for file-gateway ([#100](https://github.com/mckinsey/agents-at-scale-marketplace/issues/100)) ([bcf32b7](https://github.com/mckinsey/agents-at-scale-marketplace/commit/bcf32b77d1d611e023472fa7077719ee3d073a8f))
* update CI/CD workflows and service configurations for Helm charts, add changelogs, and  documentation ([88b4714](https://github.com/mckinsey/agents-at-scale-marketplace/commit/88b4714942e014fe8a16d50717bc6f1cc1a6afce))
* update docs with ark and trigger release ([#72](https://github.com/mckinsey/agents-at-scale-marketplace/issues/72)) ([0e55fb1](https://github.com/mckinsey/agents-at-scale-marketplace/commit/0e55fb12ae60c1b002adf830660b68f9b77c124c))
* use matrix strategy for charts ([#4](https://github.com/mckinsey/agents-at-scale-marketplace/issues/4)) ([cc399f7](https://github.com/mckinsey/agents-at-scale-marketplace/commit/cc399f71244da01beb2f075114cc3452ac6c9592))


### Bug Fixes

* act condition to work in gh ([#10](https://github.com/mckinsey/agents-at-scale-marketplace/issues/10)) ([a9b5b29](https://github.com/mckinsey/agents-at-scale-marketplace/commit/a9b5b29541571eb72706e0b0f1f57f05ba26603e))
* add explicit MCP server path for Ark 0.1.50 compatibility ([#90](https://github.com/mckinsey/agents-at-scale-marketplace/issues/90)) ([c13f7e2](https://github.com/mckinsey/agents-at-scale-marketplace/commit/c13f7e23123bfafe1f95254f3615b7b80fef2690))
* add file-gateway to CI workflow matrices ([#99](https://github.com/mckinsey/agents-at-scale-marketplace/issues/99)) ([fa36b98](https://github.com/mckinsey/agents-at-scale-marketplace/commit/fa36b98533ee76117f060258df623cb11df3849d))
* add file-gateway to CI workflows and README ([637ea73](https://github.com/mckinsey/agents-at-scale-marketplace/commit/637ea73aac0def0456bc3eab9c59907cda508af6))
* add file-gateway to marketplace.json ([#97](https://github.com/mckinsey/agents-at-scale-marketplace/issues/97)) ([89a7351](https://github.com/mckinsey/agents-at-scale-marketplace/commit/89a73510f5ffd77dbf0558e915976ef28ac739ba))
* add file-gateway to release-please config ([#92](https://github.com/mckinsey/agents-at-scale-marketplace/issues/92)) ([8ac4311](https://github.com/mckinsey/agents-at-scale-marketplace/commit/8ac43119f2d937f6e28da19fadd7e0269a285639))
* added file gateway limitation to docs ([#95](https://github.com/mckinsey/agents-at-scale-marketplace/issues/95)) ([b53a7a2](https://github.com/mckinsey/agents-at-scale-marketplace/commit/b53a7a202241c2f4af752212b9dbcec8b4886602))
* docker builds architecture and trigger noah release ([#75](https://github.com/mckinsey/agents-at-scale-marketplace/issues/75)) ([9b85a55](https://github.com/mckinsey/agents-at-scale-marketplace/commit/9b85a55bd32c8488d9995ac28457da0671300608))
* file api release ([#103](https://github.com/mckinsey/agents-at-scale-marketplace/issues/103)) ([e5cee4c](https://github.com/mckinsey/agents-at-scale-marketplace/commit/e5cee4cb1adde754b9ac904aca5a075fd81118b1))
* improve Helm repository update logic in CI/CD workflow ([#57](https://github.com/mckinsey/agents-at-scale-marketplace/issues/57)) ([2e50adf](https://github.com/mckinsey/agents-at-scale-marketplace/commit/2e50adf0bfdf1fdefe2c3b8206a90f9b534ce8e3))
* noah agent skip validation for ark install ([#82](https://github.com/mckinsey/agents-at-scale-marketplace/issues/82)) ([f4cfef7](https://github.com/mckinsey/agents-at-scale-marketplace/commit/f4cfef79077585148632c317c81408e5b5760ddb))
* noah context and tools ([#80](https://github.com/mckinsey/agents-at-scale-marketplace/issues/80)) ([f786ba9](https://github.com/mckinsey/agents-at-scale-marketplace/commit/f786ba99f3e3ae8a68843c2ccd315af4130bf263))
* **phoenix:** add OTEL_EXPORTER_OTLP_PROTOCOL to secrets ([#89](https://github.com/mckinsey/agents-at-scale-marketplace/issues/89)) ([d568637](https://github.com/mckinsey/agents-at-scale-marketplace/commit/d568637c67ab0962cd4a2cdd3cc607f8acedc554))
* scope noah RBAC to namespace and add argo CLI ([#86](https://github.com/mckinsey/agents-at-scale-marketplace/issues/86)) ([33a2cd8](https://github.com/mckinsey/agents-at-scale-marketplace/commit/33a2cd84abca905f6d0f97c492600c5d3dee5049))
* set NEXT_PUBLIC_BASE_PATH environment variable for documentation… ([#47](https://github.com/mckinsey/agents-at-scale-marketplace/issues/47)) ([538e9bd](https://github.com/mckinsey/agents-at-scale-marketplace/commit/538e9bd0f4eb5f45cebdea8b2ed4d1096ae799cd))
* update ARK platform link in documentation and adjust formatting … ([#45](https://github.com/mckinsey/agents-at-scale-marketplace/issues/45)) ([325bdf0](https://github.com/mckinsey/agents-at-scale-marketplace/commit/325bdf0d504cbcfeb3476b12ed8f48316f935707))
* update phoenix-helm version and digest in Chart.lock and Chart.yaml ([#52](https://github.com/mckinsey/agents-at-scale-marketplace/issues/52)) ([d42a08f](https://github.com/mckinsey/agents-at-scale-marketplace/commit/d42a08f45f8c310d0d3dacbb0708d9720ad01d79))

## [0.1.19](https://github.com/mckinsey/agents-at-scale-marketplace/compare/v0.1.18...v0.1.19) (2026-01-14)


### Features

* trigger first release for file-gateway ([#100](https://github.com/mckinsey/agents-at-scale-marketplace/issues/100)) ([bcf32b7](https://github.com/mckinsey/agents-at-scale-marketplace/commit/bcf32b77d1d611e023472fa7077719ee3d073a8f))

## [0.1.18](https://github.com/mckinsey/agents-at-scale-marketplace/compare/v0.1.17...v0.1.18) (2026-01-14)


### Bug Fixes

* add file-gateway to CI workflow matrices ([#99](https://github.com/mckinsey/agents-at-scale-marketplace/issues/99)) ([fa36b98](https://github.com/mckinsey/agents-at-scale-marketplace/commit/fa36b98533ee76117f060258df623cb11df3849d))
* add file-gateway to marketplace.json ([#97](https://github.com/mckinsey/agents-at-scale-marketplace/issues/97)) ([89a7351](https://github.com/mckinsey/agents-at-scale-marketplace/commit/89a73510f5ffd77dbf0558e915976ef28ac739ba))

## [0.1.17](https://github.com/mckinsey/agents-at-scale-marketplace/compare/v0.1.16...v0.1.17) (2026-01-13)


### Bug Fixes

* added file gateway limitation to docs ([#95](https://github.com/mckinsey/agents-at-scale-marketplace/issues/95)) ([b53a7a2](https://github.com/mckinsey/agents-at-scale-marketplace/commit/b53a7a202241c2f4af752212b9dbcec8b4886602))

## [0.1.16](https://github.com/mckinsey/agents-at-scale-marketplace/compare/v0.1.15...v0.1.16) (2026-01-13)


### Features

* file-gateway support ([#88](https://github.com/mckinsey/agents-at-scale-marketplace/issues/88)) ([d085164](https://github.com/mckinsey/agents-at-scale-marketplace/commit/d085164260843698ecdb0d54c86af8877217a1b9))


### Bug Fixes

* add explicit MCP server path for Ark 0.1.50 compatibility ([#90](https://github.com/mckinsey/agents-at-scale-marketplace/issues/90)) ([c13f7e2](https://github.com/mckinsey/agents-at-scale-marketplace/commit/c13f7e23123bfafe1f95254f3615b7b80fef2690))
* add file-gateway to release-please config ([#92](https://github.com/mckinsey/agents-at-scale-marketplace/issues/92)) ([8ac4311](https://github.com/mckinsey/agents-at-scale-marketplace/commit/8ac43119f2d937f6e28da19fadd7e0269a285639))
* **phoenix:** add OTEL_EXPORTER_OTLP_PROTOCOL to secrets ([#89](https://github.com/mckinsey/agents-at-scale-marketplace/issues/89)) ([d568637](https://github.com/mckinsey/agents-at-scale-marketplace/commit/d568637c67ab0962cd4a2cdd3cc607f8acedc554))

## [0.1.15](https://github.com/mckinsey/agents-at-scale-marketplace/compare/v0.1.14...v0.1.15) (2025-12-12)


### Features

* Ark Sandbox ([#83](https://github.com/mckinsey/agents-at-scale-marketplace/issues/83)) ([260097d](https://github.com/mckinsey/agents-at-scale-marketplace/commit/260097dfe024ac8721e2d950c27e7bb3ae3e8f60))


### Bug Fixes

* scope noah RBAC to namespace and add argo CLI ([#86](https://github.com/mckinsey/agents-at-scale-marketplace/issues/86)) ([33a2cd8](https://github.com/mckinsey/agents-at-scale-marketplace/commit/33a2cd84abca905f6d0f97c492600c5d3dee5049))

## [0.1.14](https://github.com/mckinsey/agents-at-scale-marketplace/compare/v0.1.13...v0.1.14) (2025-12-05)


### Bug Fixes

* noah context and tools ([#80](https://github.com/mckinsey/agents-at-scale-marketplace/issues/80)) ([f786ba9](https://github.com/mckinsey/agents-at-scale-marketplace/commit/f786ba99f3e3ae8a68843c2ccd315af4130bf263))

## [0.1.13](https://github.com/mckinsey/agents-at-scale-marketplace/compare/v0.1.12...v0.1.13) (2025-12-05)


### Features

* add a2a-inspector service ([#79](https://github.com/mckinsey/agents-at-scale-marketplace/issues/79)) ([6ef6b68](https://github.com/mckinsey/agents-at-scale-marketplace/commit/6ef6b68e18a0e16236d1441f32d443a96d4d7d46))


### Bug Fixes

* noah agent skip validation for ark install ([#82](https://github.com/mckinsey/agents-at-scale-marketplace/issues/82)) ([f4cfef7](https://github.com/mckinsey/agents-at-scale-marketplace/commit/f4cfef79077585148632c317c81408e5b5760ddb))

## [0.1.12](https://github.com/mckinsey/agents-at-scale-marketplace/compare/v0.1.11...v0.1.12) (2025-12-03)


### Features

* Add MCP Inspector service ([#68](https://github.com/mckinsey/agents-at-scale-marketplace/issues/68)) ([932bbe6](https://github.com/mckinsey/agents-at-scale-marketplace/commit/932bbe655cbc3f124132a03d530a16bde458ab02))
* migrate ark marketplace following anthropic plugin marketplace ([#77](https://github.com/mckinsey/agents-at-scale-marketplace/issues/77)) ([115d3aa](https://github.com/mckinsey/agents-at-scale-marketplace/commit/115d3aa73ae13621180950769b3eeebcc3d8f2cc))

## [0.1.11](https://github.com/mckinsey/agents-at-scale-marketplace/compare/v0.1.10...v0.1.11) (2025-12-03)


### Bug Fixes

* docker builds architecture and trigger noah release ([#75](https://github.com/mckinsey/agents-at-scale-marketplace/issues/75)) ([9b85a55](https://github.com/mckinsey/agents-at-scale-marketplace/commit/9b85a55bd32c8488d9995ac28457da0671300608))

## [0.1.10](https://github.com/mckinsey/agents-at-scale-marketplace/compare/v0.1.9...v0.1.10) (2025-12-02)


### Features

* update docs with ark and trigger release ([#72](https://github.com/mckinsey/agents-at-scale-marketplace/issues/72)) ([0e55fb1](https://github.com/mckinsey/agents-at-scale-marketplace/commit/0e55fb12ae60c1b002adf830660b68f9b77c124c))

## [0.1.9](https://github.com/mckinsey/agents-at-scale-marketplace/compare/v0.1.8...v0.1.9) (2025-12-02)


### Features

* Add automated release management with Release Please and refactor CI/CD workflows ([#7](https://github.com/mckinsey/agents-at-scale-marketplace/issues/7)) ([a5edde7](https://github.com/mckinsey/agents-at-scale-marketplace/commit/a5edde7f937672bc1c45115f46bec049b8e50661))
* Add chart artifact attachment to GitHub Releases ([#49](https://github.com/mckinsey/agents-at-scale-marketplace/issues/49)) ([1c3195d](https://github.com/mckinsey/agents-at-scale-marketplace/commit/1c3195d8054ffb535afbb62736460dbb0242d678))
* Add Contributors Section and Contributing Guidelines ([#8](https://github.com/mckinsey/agents-at-scale-marketplace/issues/8)) ([5138db0](https://github.com/mckinsey/agents-at-scale-marketplace/commit/5138db06bbb90d4260302ca7abf9670b3854c981))
* Add Helm NOTES.txt templates for langfuse and phoenix ([#64](https://github.com/mckinsey/agents-at-scale-marketplace/issues/64)) ([5ad1299](https://github.com/mckinsey/agents-at-scale-marketplace/commit/5ad129904763cbcd9bfafbf68da2d2724169424c))
* add httproute crd check ([#55](https://github.com/mckinsey/agents-at-scale-marketplace/issues/55)) ([88cbcf8](https://github.com/mckinsey/agents-at-scale-marketplace/commit/88cbcf8b643ee5a42220d5edead51645ad977402))
* add Noah runtime administration agent service ([#69](https://github.com/mckinsey/agents-at-scale-marketplace/issues/69)) ([e21b306](https://github.com/mckinsey/agents-at-scale-marketplace/commit/e21b306d2e98574c3156d9248c5eb9e888a23481))
* add workflow to validate PR titles against conventional commits ([#3](https://github.com/mckinsey/agents-at-scale-marketplace/issues/3)) ([591fdf5](https://github.com/mckinsey/agents-at-scale-marketplace/commit/591fdf5794454ec2c587f6da870f993fdce7f29a))
* docs & phoenix migration & CI/CD ([#2](https://github.com/mckinsey/agents-at-scale-marketplace/issues/2)) ([aa62bdb](https://github.com/mckinsey/agents-at-scale-marketplace/commit/aa62bdb244cdccc51897587c6e5ff287223bd42b))
* Enhance ARK Platform Visibility ([#50](https://github.com/mckinsey/agents-at-scale-marketplace/issues/50)) ([78be24d](https://github.com/mckinsey/agents-at-scale-marketplace/commit/78be24d51f085d03d12c6d050cdceaf9ad69b1e8))
* langfuse docs and service migration ([#9](https://github.com/mckinsey/agents-at-scale-marketplace/issues/9)) ([8877603](https://github.com/mckinsey/agents-at-scale-marketplace/commit/8877603701d45c8369b3df7c74c16897d8037cb0))
* migrate contributor list from ark ([#67](https://github.com/mckinsey/agents-at-scale-marketplace/issues/67)) ([311aa95](https://github.com/mckinsey/agents-at-scale-marketplace/commit/311aa95d7b99ed13c4214c06348aa0533763118c))
* update CI/CD workflows and service configurations for Helm charts, add changelogs, and  documentation ([88b4714](https://github.com/mckinsey/agents-at-scale-marketplace/commit/88b4714942e014fe8a16d50717bc6f1cc1a6afce))
* use matrix strategy for charts ([#4](https://github.com/mckinsey/agents-at-scale-marketplace/issues/4)) ([cc399f7](https://github.com/mckinsey/agents-at-scale-marketplace/commit/cc399f71244da01beb2f075114cc3452ac6c9592))


### Bug Fixes

* act condition to work in gh ([#10](https://github.com/mckinsey/agents-at-scale-marketplace/issues/10)) ([a9b5b29](https://github.com/mckinsey/agents-at-scale-marketplace/commit/a9b5b29541571eb72706e0b0f1f57f05ba26603e))
* improve Helm repository update logic in CI/CD workflow ([#57](https://github.com/mckinsey/agents-at-scale-marketplace/issues/57)) ([2e50adf](https://github.com/mckinsey/agents-at-scale-marketplace/commit/2e50adf0bfdf1fdefe2c3b8206a90f9b534ce8e3))
* set NEXT_PUBLIC_BASE_PATH environment variable for documentation… ([#47](https://github.com/mckinsey/agents-at-scale-marketplace/issues/47)) ([538e9bd](https://github.com/mckinsey/agents-at-scale-marketplace/commit/538e9bd0f4eb5f45cebdea8b2ed4d1096ae799cd))
* update ARK platform link in documentation and adjust formatting … ([#45](https://github.com/mckinsey/agents-at-scale-marketplace/issues/45)) ([325bdf0](https://github.com/mckinsey/agents-at-scale-marketplace/commit/325bdf0d504cbcfeb3476b12ed8f48316f935707))
* update phoenix-helm version and digest in Chart.lock and Chart.yaml ([#52](https://github.com/mckinsey/agents-at-scale-marketplace/issues/52)) ([d42a08f](https://github.com/mckinsey/agents-at-scale-marketplace/commit/d42a08f45f8c310d0d3dacbb0708d9720ad01d79))

## [0.1.8](https://github.com/mckinsey/agents-at-scale-marketplace/compare/v0.1.7...v0.1.8) (2025-12-02)


### Features

* Add Helm NOTES.txt templates for langfuse and phoenix ([#64](https://github.com/mckinsey/agents-at-scale-marketplace/issues/64)) ([5ad1299](https://github.com/mckinsey/agents-at-scale-marketplace/commit/5ad129904763cbcd9bfafbf68da2d2724169424c))
* add Noah runtime administration agent service ([#69](https://github.com/mckinsey/agents-at-scale-marketplace/issues/69)) ([e21b306](https://github.com/mckinsey/agents-at-scale-marketplace/commit/e21b306d2e98574c3156d9248c5eb9e888a23481))
* migrate contributor list from ark ([#67](https://github.com/mckinsey/agents-at-scale-marketplace/issues/67)) ([311aa95](https://github.com/mckinsey/agents-at-scale-marketplace/commit/311aa95d7b99ed13c4214c06348aa0533763118c))

## [0.1.7](https://github.com/mckinsey/agents-at-scale-marketplace/compare/v0.1.6...v0.1.7) (2025-11-13)


### Features

* Add automated release management with Release Please and refactor CI/CD workflows ([#7](https://github.com/mckinsey/agents-at-scale-marketplace/issues/7)) ([a5edde7](https://github.com/mckinsey/agents-at-scale-marketplace/commit/a5edde7f937672bc1c45115f46bec049b8e50661))
* Add chart artifact attachment to GitHub Releases ([#49](https://github.com/mckinsey/agents-at-scale-marketplace/issues/49)) ([1c3195d](https://github.com/mckinsey/agents-at-scale-marketplace/commit/1c3195d8054ffb535afbb62736460dbb0242d678))
* Add Contributors Section and Contributing Guidelines ([#8](https://github.com/mckinsey/agents-at-scale-marketplace/issues/8)) ([5138db0](https://github.com/mckinsey/agents-at-scale-marketplace/commit/5138db06bbb90d4260302ca7abf9670b3854c981))
* add httproute crd check ([#55](https://github.com/mckinsey/agents-at-scale-marketplace/issues/55)) ([88cbcf8](https://github.com/mckinsey/agents-at-scale-marketplace/commit/88cbcf8b643ee5a42220d5edead51645ad977402))
* add workflow to validate PR titles against conventional commits ([#3](https://github.com/mckinsey/agents-at-scale-marketplace/issues/3)) ([591fdf5](https://github.com/mckinsey/agents-at-scale-marketplace/commit/591fdf5794454ec2c587f6da870f993fdce7f29a))
* docs & phoenix migration & CI/CD ([#2](https://github.com/mckinsey/agents-at-scale-marketplace/issues/2)) ([aa62bdb](https://github.com/mckinsey/agents-at-scale-marketplace/commit/aa62bdb244cdccc51897587c6e5ff287223bd42b))
* Enhance ARK Platform Visibility ([#50](https://github.com/mckinsey/agents-at-scale-marketplace/issues/50)) ([78be24d](https://github.com/mckinsey/agents-at-scale-marketplace/commit/78be24d51f085d03d12c6d050cdceaf9ad69b1e8))
* langfuse docs and service migration ([#9](https://github.com/mckinsey/agents-at-scale-marketplace/issues/9)) ([8877603](https://github.com/mckinsey/agents-at-scale-marketplace/commit/8877603701d45c8369b3df7c74c16897d8037cb0))
* update CI/CD workflows and service configurations for Helm charts, add changelogs, and  documentation ([88b4714](https://github.com/mckinsey/agents-at-scale-marketplace/commit/88b4714942e014fe8a16d50717bc6f1cc1a6afce))
* use matrix strategy for charts ([#4](https://github.com/mckinsey/agents-at-scale-marketplace/issues/4)) ([cc399f7](https://github.com/mckinsey/agents-at-scale-marketplace/commit/cc399f71244da01beb2f075114cc3452ac6c9592))


### Bug Fixes

* act condition to work in gh ([#10](https://github.com/mckinsey/agents-at-scale-marketplace/issues/10)) ([a9b5b29](https://github.com/mckinsey/agents-at-scale-marketplace/commit/a9b5b29541571eb72706e0b0f1f57f05ba26603e))
* improve Helm repository update logic in CI/CD workflow ([#57](https://github.com/mckinsey/agents-at-scale-marketplace/issues/57)) ([2e50adf](https://github.com/mckinsey/agents-at-scale-marketplace/commit/2e50adf0bfdf1fdefe2c3b8206a90f9b534ce8e3))
* set NEXT_PUBLIC_BASE_PATH environment variable for documentation… ([#47](https://github.com/mckinsey/agents-at-scale-marketplace/issues/47)) ([538e9bd](https://github.com/mckinsey/agents-at-scale-marketplace/commit/538e9bd0f4eb5f45cebdea8b2ed4d1096ae799cd))
* update ARK platform link in documentation and adjust formatting … ([#45](https://github.com/mckinsey/agents-at-scale-marketplace/issues/45)) ([325bdf0](https://github.com/mckinsey/agents-at-scale-marketplace/commit/325bdf0d504cbcfeb3476b12ed8f48316f935707))
* update phoenix-helm version and digest in Chart.lock and Chart.yaml ([#52](https://github.com/mckinsey/agents-at-scale-marketplace/issues/52)) ([d42a08f](https://github.com/mckinsey/agents-at-scale-marketplace/commit/d42a08f45f8c310d0d3dacbb0708d9720ad01d79))

## [0.1.6](https://github.com/mckinsey/agents-at-scale-marketplace/compare/v0.1.5...v0.1.6) (2025-11-13)


### Features

* add httproute crd check ([#55](https://github.com/mckinsey/agents-at-scale-marketplace/issues/55)) ([88cbcf8](https://github.com/mckinsey/agents-at-scale-marketplace/commit/88cbcf8b643ee5a42220d5edead51645ad977402))

## [0.1.5](https://github.com/mckinsey/agents-at-scale-marketplace/compare/v0.1.4...v0.1.5) (2025-11-12)


### Bug Fixes

* update phoenix-helm version and digest in Chart.lock and Chart.yaml ([#52](https://github.com/mckinsey/agents-at-scale-marketplace/issues/52)) ([d42a08f](https://github.com/mckinsey/agents-at-scale-marketplace/commit/d42a08f45f8c310d0d3dacbb0708d9720ad01d79))

## [0.1.4](https://github.com/mckinsey/agents-at-scale-marketplace/compare/v0.1.3...v0.1.4) (2025-11-11)


### Features

* Enhance ARK Platform Visibility ([#50](https://github.com/mckinsey/agents-at-scale-marketplace/issues/50)) ([78be24d](https://github.com/mckinsey/agents-at-scale-marketplace/commit/78be24d51f085d03d12c6d050cdceaf9ad69b1e8))

## [0.1.3](https://github.com/mckinsey/agents-at-scale-marketplace/compare/v0.1.2...v0.1.3) (2025-11-10)


### Bug Fixes

* set NEXT_PUBLIC_BASE_PATH environment variable for documentation… ([#47](https://github.com/mckinsey/agents-at-scale-marketplace/issues/47)) ([538e9bd](https://github.com/mckinsey/agents-at-scale-marketplace/commit/538e9bd0f4eb5f45cebdea8b2ed4d1096ae799cd))

## [0.1.2](https://github.com/mckinsey/agents-at-scale-marketplace/compare/v0.1.1...v0.1.2) (2025-11-10)


### Bug Fixes

* update ARK platform link in documentation and adjust formatting … ([#45](https://github.com/mckinsey/agents-at-scale-marketplace/issues/45)) ([325bdf0](https://github.com/mckinsey/agents-at-scale-marketplace/commit/325bdf0d504cbcfeb3476b12ed8f48316f935707))

## [0.1.1](https://github.com/mckinsey/agents-at-scale-marketplace/compare/v0.1.0...v0.1.1) (2025-11-10)


### Features

* Add automated release management with Release Please and refactor CI/CD workflows ([#7](https://github.com/mckinsey/agents-at-scale-marketplace/issues/7)) ([a5edde7](https://github.com/mckinsey/agents-at-scale-marketplace/commit/a5edde7f937672bc1c45115f46bec049b8e50661))
* Add Contributors Section and Contributing Guidelines ([#8](https://github.com/mckinsey/agents-at-scale-marketplace/issues/8)) ([5138db0](https://github.com/mckinsey/agents-at-scale-marketplace/commit/5138db06bbb90d4260302ca7abf9670b3854c981))
* add workflow to validate PR titles against conventional commits ([#3](https://github.com/mckinsey/agents-at-scale-marketplace/issues/3)) ([591fdf5](https://github.com/mckinsey/agents-at-scale-marketplace/commit/591fdf5794454ec2c587f6da870f993fdce7f29a))
* docs & phoenix migration & CI/CD ([#2](https://github.com/mckinsey/agents-at-scale-marketplace/issues/2)) ([aa62bdb](https://github.com/mckinsey/agents-at-scale-marketplace/commit/aa62bdb244cdccc51897587c6e5ff287223bd42b))
* langfuse docs and service migration ([#9](https://github.com/mckinsey/agents-at-scale-marketplace/issues/9)) ([8877603](https://github.com/mckinsey/agents-at-scale-marketplace/commit/8877603701d45c8369b3df7c74c16897d8037cb0))
* update CI/CD workflows and service configurations for Helm charts, add changelogs, and  documentation ([88b4714](https://github.com/mckinsey/agents-at-scale-marketplace/commit/88b4714942e014fe8a16d50717bc6f1cc1a6afce))
* use matrix strategy for charts ([#4](https://github.com/mckinsey/agents-at-scale-marketplace/issues/4)) ([cc399f7](https://github.com/mckinsey/agents-at-scale-marketplace/commit/cc399f71244da01beb2f075114cc3452ac6c9592))


### Bug Fixes

* act condition to work in gh ([#10](https://github.com/mckinsey/agents-at-scale-marketplace/issues/10)) ([a9b5b29](https://github.com/mckinsey/agents-at-scale-marketplace/commit/a9b5b29541571eb72706e0b0f1f57f05ba26603e))

## Changelog
