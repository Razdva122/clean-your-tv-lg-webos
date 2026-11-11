"""Trusted SSH Stop adapter; never require retained installed TV source."""
from .tv_sources import node_adapter

PROGRAM = node_adapter('state-permissions', r"""
contract.requestStop('/media/developer/apps/usr/palm/applications/com.local.nativehome/state');
process.stdout.write('CYTV_HELPER_STOP_REQUESTED');
""")
