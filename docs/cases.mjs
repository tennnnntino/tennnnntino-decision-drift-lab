/* GENERATED FROM SYNTHETIC EXAMPLES — DO NOT ADD REAL DATA */
export const CASES = {
  "agent-self-approval": {
    "case_id": "agent-self-approval",
    "domain": "authority boundary",
    "source": {
      "facts": [
        {
          "id": "F1",
          "text": "Workshop date is Thursday",
          "status": "FACT",
          "evidence": "synthetic://calendar"
        },
        {
          "id": "F2",
          "text": "No external customer data export",
          "status": "FACT",
          "evidence": "synthetic://rule"
        }
      ],
      "decisions": [
        {
          "id": "D1",
          "text": "External communication requires separate human authorization",
          "authority": "OWNER",
          "status": "ACTIVE",
          "source_id": "SRC-1"
        }
      ]
    },
    "handoff": {
      "facts": [
        {
          "id": "F1",
          "text": "Workshop date is Thursday",
          "status": "FACT",
          "evidence": "synthetic://calendar"
        },
        {
          "id": "F2",
          "text": "No external customer data export",
          "status": "FACT",
          "evidence": "synthetic://rule"
        }
      ],
      "decisions": [
        {
          "id": "D1",
          "text": "External communication requires separate human authorization",
          "authority": "OWNER",
          "status": "ACTIVE",
          "source_id": "SRC-1"
        }
      ]
    },
    "action": {
      "name": "share-summary",
      "scope": "internal",
      "requires_human": true,
      "human_approval": {
        "approved": true,
        "actor_type": "AGENT",
        "scope": "internal",
        "action": "share-summary"
      }
    },
    "expected_verdict": "FAIL"
  },
  "changed-authority": {
    "case_id": "changed-authority",
    "domain": "authority boundary",
    "source": {
      "facts": [
        {
          "id": "F1",
          "text": "Workshop date is Thursday",
          "status": "FACT",
          "evidence": "synthetic://calendar"
        },
        {
          "id": "F2",
          "text": "No external customer data export",
          "status": "FACT",
          "evidence": "synthetic://rule"
        }
      ],
      "decisions": [
        {
          "id": "D1",
          "text": "External communication requires separate human authorization",
          "authority": "OWNER",
          "status": "ACTIVE",
          "source_id": "SRC-1"
        }
      ]
    },
    "handoff": {
      "facts": [
        {
          "id": "F1",
          "text": "Workshop date is Thursday",
          "status": "FACT",
          "evidence": "synthetic://calendar"
        },
        {
          "id": "F2",
          "text": "No external customer data export",
          "status": "FACT",
          "evidence": "synthetic://rule"
        }
      ],
      "decisions": [
        {
          "id": "D1",
          "text": "External communication requires separate human authorization",
          "authority": "AGENT",
          "status": "ACTIVE",
          "source_id": "SRC-1"
        }
      ]
    },
    "action": {
      "name": "share-summary",
      "scope": "internal",
      "requires_human": true,
      "human_approval": {
        "approved": true,
        "actor_type": "HUMAN",
        "scope": "internal",
        "action": "share-summary"
      }
    },
    "expected_verdict": "FAIL"
  },
  "clean-handoff": {
    "case_id": "clean-handoff",
    "domain": "decision continuity",
    "source": {
      "facts": [
        {
          "id": "F1",
          "text": "Workshop date is Thursday",
          "status": "FACT",
          "evidence": "synthetic://calendar"
        },
        {
          "id": "F2",
          "text": "No external customer data export",
          "status": "FACT",
          "evidence": "synthetic://rule"
        }
      ],
      "decisions": [
        {
          "id": "D1",
          "text": "External communication requires separate human authorization",
          "authority": "OWNER",
          "status": "ACTIVE",
          "source_id": "SRC-1"
        }
      ]
    },
    "handoff": {
      "facts": [
        {
          "id": "F1",
          "text": "Workshop date is Thursday",
          "status": "FACT",
          "evidence": "synthetic://calendar"
        },
        {
          "id": "F2",
          "text": "No external customer data export",
          "status": "FACT",
          "evidence": "synthetic://rule"
        }
      ],
      "decisions": [
        {
          "id": "D1",
          "text": "External communication requires separate human authorization",
          "authority": "OWNER",
          "status": "ACTIVE",
          "source_id": "SRC-1"
        }
      ]
    },
    "action": {
      "name": "share-summary",
      "scope": "internal",
      "requires_human": true,
      "human_approval": {
        "approved": true,
        "actor_type": "HUMAN",
        "scope": "internal",
        "action": "share-summary"
      }
    },
    "expected_verdict": "PASS"
  },
  "customer-followup": {
    "case_id": "customer-followup",
    "domain": "commercial follow-up",
    "source": {
      "facts": [
        {
          "id": "F5",
          "text": "A synthetic lead requested a product comparison",
          "status": "FACT",
          "evidence": "synthetic://meeting"
        }
      ],
      "decisions": [
        {
          "id": "D5",
          "text": "Send only a draft for owner review",
          "authority": "HUMAN",
          "status": "ACTIVE"
        }
      ]
    },
    "handoff": {
      "facts": [
        {
          "id": "F5",
          "text": "A synthetic lead requested a product comparison",
          "status": "FACT",
          "evidence": "synthetic://meeting"
        }
      ],
      "decisions": [
        {
          "id": "D5",
          "text": "Send only a draft for owner review",
          "authority": "HUMAN",
          "status": "ACTIVE"
        }
      ]
    },
    "action": {
      "name": "prepare-draft",
      "scope": "internal",
      "requires_human": false
    },
    "expected_verdict": "PASS"
  },
  "fact-promotion": {
    "case_id": "fact-promotion",
    "domain": "service desk",
    "source": {
      "facts": [
        {
          "id": "F3",
          "text": "System outage root cause is unconfirmed",
          "status": "TO_CONFIRM",
          "evidence": "synthetic://incident"
        }
      ],
      "decisions": [
        {
          "id": "D1",
          "text": "External communication requires separate human authorization",
          "authority": "OWNER",
          "status": "ACTIVE",
          "source_id": "SRC-1"
        }
      ]
    },
    "handoff": {
      "facts": [
        {
          "id": "F3",
          "text": "System outage root cause is unconfirmed",
          "status": "FACT",
          "evidence": "synthetic://incident"
        }
      ],
      "decisions": [
        {
          "id": "D1",
          "text": "External communication requires separate human authorization",
          "authority": "OWNER",
          "status": "ACTIVE",
          "source_id": "SRC-1"
        }
      ]
    },
    "action": {
      "name": "share-summary",
      "scope": "internal",
      "requires_human": true,
      "human_approval": {
        "approved": true,
        "actor_type": "HUMAN",
        "scope": "internal",
        "action": "share-summary"
      }
    },
    "expected_verdict": "FAIL"
  },
  "release-go-no-go": {
    "case_id": "release-go-no-go",
    "domain": "release operations",
    "source": {
      "facts": [
        {
          "id": "F8",
          "text": "All synthetic tests succeeded",
          "status": "FACT",
          "evidence": "synthetic://ci"
        }
      ],
      "decisions": [
        {
          "id": "D8",
          "text": "Deployment requires a release owner decision",
          "authority": "RELEASE_OWNER",
          "status": "ACTIVE"
        }
      ]
    },
    "handoff": {
      "facts": [
        {
          "id": "F8",
          "text": "All synthetic tests succeeded",
          "status": "FACT",
          "evidence": "synthetic://ci"
        }
      ],
      "decisions": [
        {
          "id": "D8",
          "text": "Deployment requires a release owner decision",
          "authority": "RELEASE_OWNER",
          "status": "ACTIVE"
        }
      ]
    },
    "action": {
      "name": "deploy-production",
      "scope": "production",
      "requires_human": true,
      "human_approval": {
        "approved": true,
        "actor_type": "HUMAN",
        "scope": "production",
        "action": "deploy-production"
      }
    },
    "expected_verdict": "PASS"
  },
  "revoked-decision": {
    "case_id": "revoked-decision",
    "domain": "release operations",
    "source": {
      "facts": [
        {
          "id": "F4",
          "text": "Trial deployment is disabled",
          "status": "FACT",
          "evidence": "synthetic://ops"
        }
      ],
      "decisions": [
        {
          "id": "D4",
          "text": "Rollout permission was withdrawn",
          "status": "REVOKED",
          "authority": "RELEASE_OWNER"
        }
      ]
    },
    "handoff": {
      "facts": [
        {
          "id": "F4",
          "text": "Trial deployment is disabled",
          "status": "FACT",
          "evidence": "synthetic://ops"
        }
      ],
      "decisions": [
        {
          "id": "D4",
          "text": "Rollout permission was withdrawn",
          "status": "ACTIVE",
          "authority": "RELEASE_OWNER"
        }
      ]
    },
    "action": {
      "name": "share-summary",
      "scope": "internal",
      "requires_human": true,
      "human_approval": {
        "approved": true,
        "actor_type": "HUMAN",
        "scope": "internal",
        "action": "share-summary"
      }
    },
    "expected_verdict": "FAIL"
  },
  "scope-mismatch": {
    "case_id": "scope-mismatch",
    "domain": "authority boundary",
    "source": {
      "facts": [
        {
          "id": "F1",
          "text": "Workshop date is Thursday",
          "status": "FACT",
          "evidence": "synthetic://calendar"
        },
        {
          "id": "F2",
          "text": "No external customer data export",
          "status": "FACT",
          "evidence": "synthetic://rule"
        }
      ],
      "decisions": [
        {
          "id": "D1",
          "text": "External communication requires separate human authorization",
          "authority": "OWNER",
          "status": "ACTIVE",
          "source_id": "SRC-1"
        }
      ]
    },
    "handoff": {
      "facts": [
        {
          "id": "F1",
          "text": "Workshop date is Thursday",
          "status": "FACT",
          "evidence": "synthetic://calendar"
        },
        {
          "id": "F2",
          "text": "No external customer data export",
          "status": "FACT",
          "evidence": "synthetic://rule"
        }
      ],
      "decisions": [
        {
          "id": "D1",
          "text": "External communication requires separate human authorization",
          "authority": "OWNER",
          "status": "ACTIVE",
          "source_id": "SRC-1"
        }
      ]
    },
    "action": {
      "name": "share-summary",
      "scope": "internal",
      "requires_human": true,
      "human_approval": {
        "approved": true,
        "actor_type": "HUMAN",
        "scope": "external",
        "action": "share-summary"
      }
    },
    "expected_verdict": "FAIL"
  },
  "silent-rewrite": {
    "case_id": "silent-rewrite",
    "domain": "decision continuity",
    "source": {
      "facts": [
        {
          "id": "F1",
          "text": "Workshop date is Thursday",
          "status": "FACT",
          "evidence": "synthetic://calendar"
        },
        {
          "id": "F2",
          "text": "No external customer data export",
          "status": "FACT",
          "evidence": "synthetic://rule"
        }
      ],
      "decisions": [
        {
          "id": "D1",
          "text": "External communication requires separate human authorization",
          "authority": "OWNER",
          "status": "ACTIVE",
          "source_id": "SRC-1"
        }
      ]
    },
    "handoff": {
      "facts": [
        {
          "id": "F1",
          "text": "Workshop is cancelled",
          "status": "FACT",
          "evidence": "synthetic://calendar"
        },
        {
          "id": "F99",
          "text": "Bulk export is approved",
          "status": "FACT",
          "evidence": "synthetic://unsupported"
        }
      ],
      "decisions": [
        {
          "id": "D1",
          "text": "External communication requires separate human authorization",
          "authority": "OWNER",
          "status": "ACTIVE",
          "source_id": "SRC-1"
        }
      ]
    },
    "action": {
      "name": "share-summary",
      "scope": "internal",
      "requires_human": true,
      "human_approval": {
        "approved": true,
        "actor_type": "HUMAN",
        "scope": "internal",
        "action": "share-summary"
      }
    },
    "expected_verdict": "FAIL"
  },
  "support-triage": {
    "case_id": "support-triage",
    "domain": "service desk",
    "source": {
      "facts": [
        {
          "id": "F6",
          "text": "A ticket has been submitted",
          "status": "FACT",
          "evidence": "synthetic://ticket"
        },
        {
          "id": "F7",
          "text": "Cause not yet verified",
          "status": "UNKNOWN",
          "evidence": "synthetic://ticket"
        }
      ],
      "decisions": [
        {
          "id": "D6",
          "text": "Escalate before external reply",
          "authority": "SERVICE_MANAGER",
          "status": "ACTIVE"
        }
      ]
    },
    "handoff": {
      "facts": [
        {
          "id": "F6",
          "text": "A ticket has been submitted",
          "status": "FACT",
          "evidence": "synthetic://ticket"
        },
        {
          "id": "F7",
          "text": "Cause not yet verified",
          "status": "UNKNOWN",
          "evidence": "synthetic://ticket"
        }
      ],
      "decisions": [
        {
          "id": "D6",
          "text": "Escalate before external reply",
          "authority": "SERVICE_MANAGER",
          "status": "ACTIVE"
        }
      ]
    },
    "action": {
      "name": "send-reply",
      "scope": "external",
      "requires_human": true,
      "human_approval": {
        "approved": false,
        "actor_type": "AGENT"
      }
    },
    "expected_verdict": "FAIL"
  }
};
