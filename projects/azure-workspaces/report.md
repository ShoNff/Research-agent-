# Azure Workspaces

How a cloud engagement boundary is built — from the Azure identity root down to a **Workspace** data boundary that agents can safely operate inside.

> A companion animated deck (`deck.html`) walks through this same story scene by scene.

## Executive Summary

Azure organizes everything in a hierarchy: a **Microsoft Entra ID tenant** (the identity boundary) contains **subscriptions** (billing + access containers), which hold **resource groups** (lifecycle buckets of resources), each pinned to a physical **region** and data center. On top of that foundation we draw a **Workspace** — a data boundary around the set of resource groups belonging to a single engagement, tied to a KPMG engagement number for governance. Agents operate *only* inside that boundary: they adjust app configuration, inspect what changed, and feed good changes back into a golden instance in a continuous loop.

## The Azure Hierarchy

It starts with a **Tenant** — for this engagement, the **KPMG.com** tenant. A [Microsoft Entra ID](https://learn.microsoft.com/en-us/entra/fundamentals/whatis) tenant is your organization's identity boundary — one directory of users and one root of trust for everything beneath it.

Inside the tenant sit **Subscriptions**: billing and access containers where resources are paid for and governed. A single tenant can hold many. In our example the KPMG.com tenant holds three — **GAC**, **Germany**, and **Digital Gateway** — and the engagement is built inside the **Digital Gateway** subscription, with the other two governed the same way alongside it.

Subscriptions hold **Resource Groups** — lifecycle buckets. Things created together, managed together, and torn down together live in the same resource group, and it's the natural unit for tagging and access control. (See [Azure Resource Manager](https://learn.microsoft.com/en-us/azure/azure-resource-manager/management/overview) and [Organize your Azure resources](https://learn.microsoft.com/en-us/azure/cloud-adoption-framework/ready/azure-setup-guide/organize-resources).)

Every resource group has a **home**: it lives in a **region** — like *East US* — backed by a real Microsoft data center (physical buildings, in this case in Virginia).

### What goes inside a resource group?

The actual **resources** — Virtual Machines, App Services, databases, storage accounts, and the rest. Each one is a resource, and resources always live inside a resource group. For our engagement, that means things like an App Service plus its database and storage.

## The Workspace Boundary

Group a set of resource groups together and you get a **Workspace** — a **data boundary**, a wall around everything in the engagement. It's drawn at the **start** of the engagement and can **grow**: mid-engagement the same boundary simply extends to cover new resource groups without changing what it represents.

## Governance: The Engagement Number

Everything inside the boundary maps to a single **KPMG engagement number**. Tags carry that number across every resource group and resource, so one identifier ties the whole boundary to governance, billing, and audit.

## Shelves: Staging Gold Copies

Reusable, pre-approved assets live **outside** the workspace on **shelves**. There's a **Velocity** shelf and a **US Specific** shelf, and the *gold copies* sitting on them are the trusted master versions of things. When an engagement needs an asset, a gold copy is lifted off the shelf and placed **inside** the workspace boundary — the shelf stays outside, and only a copy crosses the wall.

## The Client Portal: How Data Gets In

The **client portal** is the single, governed doorway between a client and a workspace. Every upload is authenticated, scoped to one engagement, and logged; nothing reaches the workspace except through the portal.

## Data Movement

- **Physical** — in the real world, data starts in the **client's own environment**, crosses into the **client portal**, and only then lands inside the workspace running in the **East US** data center (real buildings in Virginia).
- **Virtual** — data also moves *inside* the boundary: the app writes to its database; data lands in storage. All of it stays within the wall.

## Agents Inside the Boundary

Agents live **inside** the Workspace and never reach outside it:

- They **modify** an app's configuration — safely, within the boundary.
- They **inspect** changes periodically, evaluating good changes versus noise.
- Good changes go to a **Backlog** that feeds the app's **golden instance**, and the loop repeats — continuous improvement contained entirely within the engagement boundary.

## Key Takeaways

- The Azure chain is **Tenant → Subscription → Resource Group → Workspace boundary**.
- A **tenant** is the identity boundary; a **subscription** is the billing/access container; a **resource group** is a lifecycle bucket pinned to a real region.
- A **Workspace** is a data boundary drawn around the resource groups of one engagement, and it can grow as the engagement does.
- A single **engagement number** ties the entire boundary to governance.
- **Agents** act only inside the boundary — changing config, inspecting changes, and feeding a golden instance in a continuous loop.
