# AI Usage Report

**AI TOOL USED:** Claude (Anthropic)

## HOW AI WAS USED:

AI assistance was used as a development aid for parts of the Django implementation. It helped with initial scaffolding and with suggestions for models, forms, views, templates, URL routing, seed data, and the deadline-aware priority engine. It was also used to help investigate a template error during testing.

The project was not produced from a generic prompt. I provided the requirements, user roles, ticket workflow, category rules, priority examples, and database expectations, then reviewed and adapted the implementation to fit the project.

## MY CONTRIBUTION:

I defined the product requirements and the complete workflow: a student raises a ticket, priority is determined, the request is routed to staff, additional information can be requested, and the ticket is resolved or declined. I also specified the fee and attendance deadline examples, the roles and permissions, the database fields, and the need for priority to update without a background scheduler.

I chose the server-rendered Django approach, reviewed the data model and priority rules, decided which features belonged in the current version, and made changes during implementation. I also ran the application, checked the main role-based workflows, and reviewed the final behavior rather than accepting generated code without testing it.

## ISSUE FOUND DURING REVIEW:

A `TemplateSyntaxError` in `ticket_detail.html`: the actions panel used `{% if ticket.is_open and (user.is_head or ticket.assigned_to_id == user.id) %}` — Django's template `{% if %}` tag does not support parentheses for grouping conditions, unlike Python itself.

## HOW IT WAS FIXED:

During the role-based test walkthrough, the staff/head ticket detail page exposed the malformed template condition. The permission check was moved into the view as `can_process`, and the template was simplified to use that value. I reviewed the change and reran the relevant workflow checks, including the more-info exchange and student-isolation permissions.