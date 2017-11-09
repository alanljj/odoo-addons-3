# -*- coding: utf-8 -*-
# Copyright(C) 2017 Patrik Dufresne Service Logiciel inc. (http://www.patrikdufresne.com).
{
    "name": "Project Sprint",
    "version": "8.0.1",
    "author": "Patrik Dufresne Service Logiciel inc.",
    "website": "http://www.patrikdufresne.com/",
    "license": "AGPL-3",
    "category": "Project",
    "description": """
Provide Sprint kanban view to Project module to allow planning of task using Agile sprint concept.
""",
    "depends": [
        "project",
    ],
    "demo": [],
    "data": [
        "security/security_project_sprint.xml",
        "security/ir.model.access.csv",
        "view/project_sprint_view.xml",
        "view/project_view.xml",
        "project_sprint_data.xml",
    ],
    "installable": True,
    "active": False
}
