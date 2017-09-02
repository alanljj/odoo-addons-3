# -*- coding: utf-8 -*-
# Copyright(C) 2017 Patrik Dufresne Service Logiciel inc. (http://www.patrikdufresne.com).
{
    "name": "Project Task Sequence",
    "version": "8.0.1",
    "author": "Patrik Dufresne Service Logiciel inc.",
    "website": "http://www.patrikdufresne.com/",
    "license": "AGPL-3",
    "category": "Project",
    "description": """
Create a new identifier for each task. By default it's used the pattern TASK-123. The task identifier is also displayed in various views for better tracking.
""",
    "depends": [
        "project",
    ],
    "data": [
        "views/project_view.xml",
        "project_task_sequence.xml",
    ],
    "installable": True,
    "active": False
}
