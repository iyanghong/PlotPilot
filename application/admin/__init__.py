# application/admin/__init__.py
"""后台管理应用服务 — 作者：Axelton

自包含的 admin 应用层，通过 DashboardService / UserAdminService / BookAdminService
提供后台管理所需的聚合查询和 CRUD 编排。仅读取现有 Repository，不修改它们。
"""
