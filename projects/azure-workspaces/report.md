# Azure Workspaces

How a cloud engagement boundary is built — from the Azure identity root down to a **Workspace** data boundary that agents can safely operate inside.

> A companion animated deck (`deck.html`) walks through this same story scene by scene.

## Executive Summary

Azure organizes everything in a hierarchy: a **Microsoft Entra ID tenant** (the identity boundary) contains **subscriptions** (billing + access containers), which hold **resource groups** (lifecycle buckets of resources), each pinned to a physical **region** and data center. On top of that foundation we draw a **Workspace** — a data boundary around the set of resource groups belonging to a single engagement, tied to a KPMG engagement number for governance. Agents operate *only* inside that boundary: they adjust app configuration, inspect what changed, and feed good changes back into a golden instance in a continuous loop.

## The Azure Hierarchy

It starts with a **Tenant**. A [Microsoft Entra ID](https://learn.microsoft.com/en-us/entra/fundamentals/whatis) tenant is your organization's identity boundary — one directory of users and one root of trust for everything beneath it.

Inside the tenant sits a **Subscription**: a billing and access container where resources are paid for and governed. A single tenant can hold many subscriptions.

Subscriptions hold **Resource Groups** — lifecycle buckets. Things created together, managed together, and torn down together live in the same resource group, and it's the natural unit for tagging and access control. (See [Azure Resource Manager](https://learn.microsoft.com/en-us/azure/azure-resource-manager/management/overview) and [Organize your Azure resources](https://learn.microsoft.com/en-us/azure/cloud-adoption-framework/ready/azure-setup-guide/organize-resources).)

Every resource group has a **home**: it lives in a **region** — like *East US* — backed by a real Microsoft data center (physical buildings, in this case in Virginia).

### What goes inside a resource group?

The actual **resources** — Virtual Machines, App Services, databases, storage accounts, and the rest. Each one is a resource, and resources always live inside a resource group. For our engagement, that means things like an App Service plus its database and storage.

## The Workspace Boundary

Group a set of resource groups together and you get a **Workspace** — a **data boundary**, a wall around everything in the engagement. It's drawn at the **start** of the engagement and can **grow**: mid-engagement the same boundary simply extends to cover new resource groups without changing what it represents.

## Governance: The Engagement Number

Everything inside the boundary maps to a single **KPMG engagement number**. Tags carry that number across every resource group and resource, so one identifier ties the whole boundary to governance, billing, and audit.

## Data Movement

- **Physical** — data moves across the country over real fiber, replicating between real data centers.
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
