<p align="center">
  <img src="./docs/static/qoobot-logo.svg" alt="QooBot" width="600">
</p>

<p align="center">
  <strong>Open Source, Open Standard, For All Robots.</strong>
</p>

<p align="center">
  <a href="https://github.com/qoobots/qoobot/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-Apache%202.0-blue.svg" alt="License"></a>
  <a href="https://github.com/qoobots/qoobot/stargazers"><img src="https://img.shields.io/github/stars/qoobots/qoobot?style=social" alt="Stars"></a>
  <a href="https://github.com/qoobots/qoobot/network/members"><img src="https://img.shields.io/github/forks/qoobots/qoobot?style=social" alt="Forks"></a>
  <a href="https://discord.gg/qoobot"><img src="https://img.shields.io/badge/community-discord-5865F2?logo=discord&amp;logoColor=white" alt="Discord"></a>
  <a href="https://github.com/qoobots/qoobot/discussions"><img src="https://img.shields.io/badge/discussions-welcome-181717?logo=github" alt="Discussions"></a>
</p>

<p align="center">
  <a href="./README.md">中文</a> |
  <a href="#-what-is-qoobot">Overview</a> •
  <a href="#-vision--mission">Vision</a> •
  <a href="#-why-qoobot">Why</a> •
  <a href="#-industry-comparison">Comparison</a> •
  <a href="#-architecture">Architecture</a> •
  <a href="#-projects">Projects</a> •
  <a href="#-getting-started">Get Started</a> •
  <a href="#-roadmap">Roadmap</a> •
  <a href="#-community">Community</a> •
  <a href="#-license">License</a>
</p>

---

## 🤖 What is QooBot?

QooBot is an **open-source, full-stack ecosystem** for humanoid robots. We are building the universal operating system that powers the next generation of physical AI — with humanoid robots at the core, spanning industrial, service, and home applications.

> One brain. Any body. Everywhere.

Our mission is to do for robotics what open-source operating systems did for computing: **democratize access, accelerate innovation, and build a global community** around shared infrastructure.

---

## 🔭 Vision &amp; Mission

> See details: [`docs/01_战略与产品/01愿景与使命.md`](./docs/01_战略与产品/01愿景与使命.md)

QooBot's grand vision — **Humanoid robots are not tools, but an extension of human civilization.**

| # | Vision | Core Idea |
|:--:|------|----------|
| ① | **Full Job Replacement** | Humanoid robots take over all repetitive jobs — manufacturing, agriculture, logistics, construction, food service, healthcare, etc. |
| ② | **10,000× Productivity** | Autonomous production + self-maintenance + self-replication closed loop. GDP per capita reaches $120M. Post-scarcity era. |
| ③ | **Robot Economy** | Global GDP created by robots. Humans share wealth via UBI, skill royalties, and robot asset securitization (R-REITs). |
| ④ | **Consciousness Upload** | BCI → motor fusion → consciousness migration → multi-body existence. Robots become humanity's second body. |
| ⑤ | **Extreme Environments** | Deep sea 11,000m, mantle 10km+, Antarctic subglacial lakes, active volcanoes, nuclear zones — robots explore the forbidden. |
| ⑥ | **Mars Colonization** | One million robots land first, build a city in 10 years. Humans arrive with suitcases. |
| ⑦ | **Robot Starships** | Autonomous interstellar platforms piloted, maintained, and decided by humanoid robots — to Europa, Titan, Proxima Centauri. |
| ⑧ | **Dyson Sphere** | A billion self-replicating robots spend 1,000 years building a solar megastructure. Humanity becomes Type II civilization. |
| ⑨ | **Interstellar Civilization** | Von Neumann probe colonization wave. The entire Milky Way covered within 1 million years. |
| ⑩ | **Symbiosis of All** | Humans, robots, AI, and nature in four-element harmony. Heal Earth's ecology, evolve into an interstellar species. |

> **QooBot's Ultimate Mission**: Not just to build a robot, but to ignite a spark of civilization — transforming humanity from a terrestrial species into an interstellar one.

---

## 🧭 Why QooBot?

| Challenge | QooBot's Answer |
|-----------|----------------|
| 🧩 **Fragmentation** — Every humanoid robot runs proprietary software, no reuse across platforms | **Unified OS** — A single brain OS that works across humanoid robot morphologies and manufacturers |
| 🔒 **Vendor Lock-in** — Closed ecosystems limit choice and innovation | **Open Standard** — Apache 2.0 licensed, community-driven, fork-friendly |
| 🐌 **Slow Progress** — Everyone reinvents perception, planning, and control from scratch | **Shared Foundation** — Production-grade modules for perception, cognition, motion, and more |
| 🌍 **High Barrier** — Robotics development requires deep expertise across too many domains | **Developer First** — Rich SDK, simulator, debugger, and a global skill marketplace |
| ⚡ **Edge to Cloud** — No unified stack for on-device + cloud intelligence | **Seamless Scale** — From on-chip inference to cloud collaboration |

---

## 🆚 Industry Comparison

### 🌏 International Competitors

| Dimension | **QooBot** | **Boston Dynamics** | **Tesla (Optimus)** | **Figure AI** | **1X Technologies** |
|------|:---:|:---:|:---:|:---:|:---:|
| **Positioning** | Open-source full-stack robot OS | High-dynamic motion &amp; special-purpose robots | General-purpose humanoid + automotive automation | General-purpose humanoid + warehouse logistics | Home service humanoid robots |
| **Core Product** | qoobrain OS + full-stack open ecosystem | Atlas / Spot / Stretch | Optimus | Figure 02 | NEO / EVE |
| **Software Strategy** | 🟢 Fully open-source (Apache 2.0) | 🔴 Fully closed | 🔴 Fully closed | 🔴 Closed commercial | 🔴 Closed commercial |
| **Hardware Openness** | 🟢 Reference design open, any hardware | 🔴 Closed hardware | 🔴 Closed hardware | 🔴 Closed hardware | 🔴 Closed hardware |
| **Operating System** | Self-developed qoobrain Brain OS | Proprietary internal OS | FSD + Dojo based | Self-developed Helix model | Proprietary internal system |
| **On-device AI** | 🟢 qoocore chip-level acceleration | 🟡 Custom compute platform | 🟢 Self-developed Dojo + HW4.0 | 🟡 OpenAI cloud models | 🟡 Self-developed on-device models |
| **Cloud Capability** | 🟢 qoocloud multi-robot orchestration | 🔴 Limited cloud support | 🟢 Dojo supercomputing cluster | 🟡 Relies on OpenAI cloud | 🟡 Basic cloud sync |
| **Developer Ecosystem** | 🟢 IDE plugins/simulator/skill marketplace | 🔴 Internal only | 🔴 Internal only | 🔴 Internal only | 🔴 Internal only |
| **Skill Marketplace** | 🟢 qoostore third-party skill distribution | ❌ None | ❌ None | ❌ None | ❌ None |
| **Simulation Platform** | 🟢 Isaac Sim + MuJoCo deep integration | 🟡 Internal simulation | 🟢 Custom sim + real factory | 🟡 Internal simulation | 🟡 Internal simulation |
| **Multi-Robot Collaboration** | 🟢 Native multi-robot framework | 🔴 Limited support | 🟡 Factory scenario collaboration | 🟡 Warehouse scenario | 🔴 Planned |
| **Safety &amp; Compliance** | 🟢 Full compliance framework (ISO 10218/13482) | 🟢 Military-grade safety | 🟡 Automotive standards ported | 🟡 Basic safety | 🟡 Basic safety |
| **Supply Chain** | 🟢 qoochain open manufacturing standards | 🔴 Self-controlled supply chain | 🟢 Gigafactory mass production | 🔴 Self-controlled supply chain | 🔴 Self-controlled supply chain |
| **Hardware Blueprints** | 🟢 Fully open-source (mechanical/circuit/PCB) | 🔴 Not public | 🔴 Not public | 🔴 Not public | 🔴 Not public |
| **Target Scenarios** | Industrial/service/home — all scenarios | Industrial inspection/military/research | Auto manufacturing/warehouse/home | Warehouse logistics/manufacturing | Home service/light industry |
| **Business Model** | Open ecosystem + enterprise services | Hardware sales + service contracts | Self-use + future sales | Hardware sales + B2B | Hardware sales + subscription |
| **Funding/Valuation** | Community-driven | Hyundai Motor (valued ~$11B) | Tesla internal (Optimus standalone ~$1T远期) | $675M+ raised (valued ~$2.6B) | $100M+ raised (OpenAI backed) |

### 🌏 Chinese Competitors

| Dimension | **QooBot** | **Unitree Robotics** | **XPeng Robotics** | **AGIBOT** |
|------|:---:|:---:|:---:|:---:|
| **Positioning** | Open-source full-stack robot OS | High-performance general-purpose humanoid | AI-defined cars + humanoid robots | Embodied intelligence general-purpose robots |
| **Core Product** | qoobrain OS + full-stack open ecosystem | H1 / G1 humanoid robots | Iron humanoid robot | Yuanzheng A2 series |
| **Software Strategy** | 🟢 Fully open-source (Apache 2.0) | 🟡 Partially open (SDK/API) | 🔴 Closed commercial | 🟡 Limited open |
| **Hardware Openness** | 🟢 Reference design open, any hardware | 🟡 Self-developed body, third-party expansion | 🔴 Closed hardware system | 🟡 Self-developed body focused |
| **Operating System** | Self-developed qoobrain Brain OS | Linux + ROS based | Self-developed XBrain | Self-developed GO-1 Brain |
| **On-device AI** | 🟢 qoocore chip-level acceleration | 🟡 NVIDIA Jetson | 🟡 Self-developed chip (Turing) | 🟡 General-purpose accelerator cards |
| **Cloud Capability** | 🟢 qoocloud multi-robot orchestration | 🔴 Limited cloud support | 🟡 XNet cloud collaboration | 🟡 Cloud training platform |
| **Developer Ecosystem** | 🟢 IDE plugins/simulator/skill marketplace | 🟡 SDK/API | 🔴 Internal development only | 🟡 Basic SDK |
| **Skill Marketplace** | 🟢 qoostore third-party skill distribution | ❌ None | ❌ None | ❌ None |
| **Simulation Platform** | 🟢 Isaac Sim + MuJoCo deep integration | 🟡 Basic simulation | 🟡 Internal simulation | 🟡 Basic simulation |
| **Multi-Robot Collaboration** | 🟢 Native multi-robot framework | 🟡 Limited support | 🔴 Planned | 🟡 Planned |
| **Safety &amp; Compliance** | 🟢 Full compliance framework (ISO 10218/13482) | 🟡 Basic safety | 🟡 Automotive standards ported | 🟡 Basic safety |
| **Supply Chain** | 🟢 qoochain open manufacturing standards | 🟡 Self-controlled supply chain | 🟡 Self-controlled supply chain | 🟡 Self-controlled supply chain |
| **Hardware Blueprints** | 🟢 Fully open-source (mechanical/circuit/PCB) | 🔴 Not public | 🔴 Not public | 🔴 Not public |
| **Target Scenarios** | Industrial/service/home — all scenarios | Research/inspection/home | Auto manufacturing/home service | Industrial manufacturing/logistics |
| **Business Model** | Open ecosystem + enterprise services | Hardware sales | Hardware + closed ecosystem | Hardware sales + platform |

### Key Differentiators Summary

| Dimension | QooBot Advantage | Industry Status |
|----------|:-----------:|:-----------:|
| **Open-Source Depth** | Full-stack Apache 2.0, from chip to cloud | Most vendors only open SDK or API; core software fully closed |
| **Hardware Neutrality** | Adapts to any hardware, no vendor lock-in | Software deeply bound to proprietary hardware |
| **Ecosystem Openness** | Skill marketplace + accessory certification + community-driven | Closed ecosystems; third-party extensions extremely limited |
| **Developer Experience** | Complete IDE toolchain + simulation + debugging | Lack of professional robot development tooling; internal tools not public |
| **Extensibility** | Modular architecture, unified from MCU to cloud | Fragmented systems, no unified abstraction |
| **Cost Barrier** | Zero-cost startup, open-source community driven | High hardware purchase cost (Atlas ~$150K+, Optimus pricing undisclosed) |
| **Hardware Blueprints** | Mechanical/circuit/PCB fully open, self-manufacturable | All vendors keep hardware designs completely closed |

> 💡 QooBot provides not only an **open-source brain** that powers all robots, but also a complete **hardware reference design &amp; manufacturing solution** — from mechanical drawings, circuit schematics to PCB layouts, all open-source. Anyone can build their own robot body. This "software + hardware, full-stack open" model makes QooBot the **Android + Open Hardware** of robotics. Whether Boston Dynamics, Tesla, Figure AI, 1X, Unitree, XPeng, or AGIBOT — all can build upon or adapt QooBot's full-stack ecosystem to reduce R&amp;D costs, accelerate product iteration, and break vendor lock-in.

---

## 🏗 Architecture

<p align="center">
  <img src="./docs/static/architecture.svg" alt="QooBot Architecture" width="100%">
</p>

QooBot is organized by **deployment platform** into **6 platform directories**:

### 🤖 qoobot-os — Humanoid Robot OS

The complete operating system running on robot hardware:

| Module | Description |
|---------|-------------|
| **[hal](./qoobot-os/hal/)** | **Hardware Abstraction Layer** — Sensor interfaces, actuator drivers, compute platform specs, mechanical &amp; energy reference designs. |
| **[ai-engine](./qoobot-os/ai-engine/)** | **AI Inference Engine** — On-device model compilation, NPU/GPU/DSP multi-backend dispatch, chip-level acceleration. |
| **[brain](./qoobot-os/brain/)** | **Brain Core** — Perception, cognition, decision-making, motion planning, real-time control. The central nervous system. |
| **[services](./qoobot-os/services/)** | **System Services** — Voice assistant, spatial understanding, navigation, self-diagnostics, multi-robot connectivity. |
| **[edge](./qoobot-os/edge/)** | **Edge Modules** — On-device SDKs (auth/accessory/skill runtime). |

### 🌐 qoobot-web — Browser Web Apps

| Module | Description |
|---------|-------------|
| **[portal](./qoobot-web/portal/)** | **Brand Site** — Product showcase, PWA. |
| **[admin](./qoobot-web/admin/)** | **Admin Console** — Account, device, security management. |
| **[community](./qoobot-web/community/)** | **Global Community** — Forums, academy, events, contributor network. |
| **[gear](./qoobot-web/gear/)** | **Accessory Portal** — MFQ certification, developer center, standards. |
| **[remote](./qoobot-web/remote/)** | **Teleoperation Panel** — WebRTC remote control, teaching records. |
| **[dev-dashboard](./qoobot-web/dev-dashboard/)** | **Developer Dashboard** — Simulation monitoring, performance analysis. |

### 🖥️ qoobot-desktop — Desktop Software

| Module | Description |
|---------|-------------|
| **[cli](./qoobot-desktop/cli/)** | **CLI Toolchain** — Project init, compile, debug, package, deploy. |
| **[lsp](./qoobot-desktop/lsp/)** | **LSP Server** — Code completion, diagnostics, navigation. |
| **[vscode-plugin](./qoobot-desktop/vscode-plugin/)** | **VS Code Plugin** — Integrated development environment. |
| **[python-sdk](./qoobot-desktop/python-sdk/)** | **Python SDK** — Robot application development. |

### ☁️ qoobot-service — Cloud Microservices

| Module | Description |
|---------|-------------|
| **[auth](./qoobot-service/auth/)** | **Identity &amp; Auth** — Unified identity, OAuth, API Key, device trust. |
| **[community](./qoobot-service/community/)** | **Community Services** — Forums, content, governance. |
| **[cloud](./qoobot-service/cloud/)** | **Cloud Platform** — Remote inference, fleet mgmt, OTA, digital twin, observability. |
| **[chain](./qoobot-service/chain/)** | **Supply Chain** — Manufacturing, calibration, QA, BOM. |
| **[compliance](./qoobot-service/compliance/)** | **Regulatory Compliance** — Safety standards, wireless certs, export controls, privacy. |
| **[gear](./qoobot-service/gear/)** | **Accessory Services** — MFQ certification, lab management. |
| **[store](./qoobot-service/store/)** | **Skill Store** — Skill publishing, orders, analytics. |

### 📱 qoobot-mobile — Mobile App (Planned)

> 🚧 To be developed — Android/iOS native app. Planned: login, remote control, live monitoring, community.

### 🔌 qoobot-proto — Cross-Platform Protocols

> **[Protocol Index](./qoobot-proto/)** — Defines all cross-platform gRPC/Protobuf communication contracts.

---

## 🚀 Getting Started

### Prerequisites

- **Python** ≥ 3.10
- **Node.js** ≥ 20
- **CUDA** ≥ 12.0 (optional, for GPU acceleration)

### Quick Start

```bash
# Clone the monorepo
git clone https://github.com/qoobots/qoobot.git
cd qoobot/qoobot-os/brain

# Install dependencies
pip install -e ".[dev]"

# Run the brain OS
python -m brain_ai.launch

# Run the test suite
pytest tests/ -v
```

### Build Your First Skill

```python
from qoobrain import Skill, Perception, Action

class PickAndPlace(Skill):
    """A simple pick-and-place skill."""

    def setup(self):
        self.perception = Perception(cameras=["front_rgbd"])
        self.action = Action(controller="arm_6dof")

    async def run(self, target: str):
        obj = await self.perception.detect(target)
        grasp = await self.action.plan_grasp(obj)
        await self.action.execute(grasp)
```

---

## 📊 Project Status

> **All 12 sub-projects completed design and migrated to 6 platform directories. 525 feature modules — 100% complete.**

| # | Platform | Module | Version | Status | Progress |
|---|------|------|---------|------|:--:|
| 1 | **qoobot-os** | brain | v1.0.0-alpha | 🟢 **Alpha** | 10/10 |
| 2 | qoobot-os | hal | v1.0 | 🟢 **Complete** | 43/43 |
| 3 | qoobot-os | ai-engine | v0.5 | 🟢 **Complete** | 40/40 |
| 4 | qoobot-os | services | v0.3 | 🟢 **Complete** | 48/48 |
| 5 | **qoobot-service** | auth | v0.6 | 🟢 **Complete** | 59/59 |
| 6 | qoobot-service | cloud | v0.3 | 🟢 **Complete** | 45/45 |
| 7 | qoobot-service | compliance | v0.3 | 🟢 **Complete** | 42/42 |
| 8 | qoobot-service | store | v0.1 | 🟢 **Complete** | 45/45 |
| 9 | qoobot-service | chain | v0.1 | 🟢 **Complete** | 36/36 |
| 10 | qoobot-service | gear | v0.1 | 🟢 **Complete** | 36/36 |
| 11 | qoobot-service | community | v0.1 | 🟢 **Complete** | 38/38 |
| 12 | **qoobot-web** | portal | v1.0 | 🟢 **Complete** | 19/19 |
| 13 | qoobot-web | remote | v0.3 | 🟢 **Complete** | 10/10 |
| 14 | **qoobot-desktop** | cli/lsp/plugin | v1.0 | 🟢 **Complete** | 56/56 |
| 15 | **qoobot-mobile** | — | — | ⚪ **Planned** | 0 |

---

## 🗺 Roadmap

### ✅ Current (v1.0 — All Sub-projects Design Complete)

- [x] Core brain OS: perception, planning, decision engine (qoobot-os/brain Alpha)
- [x] On-device AI inference engine (qoobot-os/ai-engine v0.5, 40/40 complete)
- [x] Hardware reference design (qoobot-os/hal, 43/43 all ready)
- [x] Unified identity infrastructure (qoobot-service/auth v0.6, 59/59 complete)
- [x] Developer toolchain (qoobot-desktop, 56/56 complete)
- [x] System services (qoobot-os/services v0.3, 48/48 complete)
- [x] Cloud services (qoobot-service/cloud v0.3, 45/45 complete)
- [x] Regulatory compliance (qoobot-service/compliance v0.3, 42/42 complete)
- [x] Remote control (qoobot-web/remote v0.3, 10/10 complete)
- [x] Skill marketplace (qoobot-service/store v0.1, 45/45 complete)
- [x] Supply chain manufacturing (qoobot-service/chain v0.1, 36/36 complete)
- [x] Accessory ecosystem (qoobot-service/gear v0.1, 36/36 complete)
- [x] Open source community (qoobot-service/community v0.1, 38/38 complete)
- [x] Official website (qoobot-web/portal v1.0, 19/19 complete)
- [ ] Mobile App (qoobot-mobile — planned)

### Next (v1.1+ — Deep Implementation & Hardware Validation)

- [ ] qoobot-os/brain real robot deployment on ≥ 3 platforms
- [ ] Simulation environment (Isaac Sim + MuJoCo) deep refinement
- [ ] Skill SDK v1.0 with developer documentation
- [ ] On-device inference compiler performance benchmarks
- [ ] Multi-robot collaboration framework hardware validation
- [ ] Annual developer conference

---

## 🌍 Community

QooBot is built by and for the global robotics community.

| Channel | Link |
|---------|------|
| 💬 **Discord** | [Join our Discord](https://discord.gg/qoobot) |
| 💡 **Discussions** | [GitHub Discussions](https://github.com/qoobots/qoobot/discussions) |
| 🐛 **Issues** | [Report a bug](https://github.com/qoobots/qoobot/issues) |
| 📖 **Docs** | [Documentation](https://docs.qoobot.dev) (coming soon) |
| 🎓 **Academia** | Partner with us: `research@qoobot.dev` |

### Contributing

We welcome contributions of all kinds — code, documentation, hardware designs, research, and community building.

```bash
# Fork &amp; clone
git clone https://github.com/YOUR_USERNAME/qoobot.git

# Create a branch
git checkout -b feat/your-feature

# Make changes &amp; test
pytest tests/ -v

# Submit a PR
```

See [CONTRIBUTING.md](./CONTRIBUTING.md) for our full contributor guide.

### Governance

QooBot follows an open governance model inspired by successful open-source foundations. Project decisions are made transparently through RFCs and community consensus. Maintainers are nominated based on sustained contribution merit.

---

## 🤝 Partners &amp; Adopters

<p align="center">
  <em>We are actively building our partner network. If your organization is interested in adopting QooBot or collaborating on its development, reach out to <a href="mailto:partners@qoobot.dev">partners@qoobot.dev</a>.</em>
</p>

---

## 📄 License

```
Copyright 2024-2026 The QooBot Authors

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
```

All platform directories in this monorepo are licensed under **[Apache License 2.0](./LICENSE)** .

---

<p align="center">
  <sub>Built with ❤️ by the global robotics community. One brain. Any body. Everywhere.</sub>
</p>
