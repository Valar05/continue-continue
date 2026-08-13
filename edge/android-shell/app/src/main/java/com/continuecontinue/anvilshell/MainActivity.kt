package com.continuecontinue.anvilshell

import android.Manifest
import android.app.Activity
import android.content.Intent
import android.os.Build
import android.os.Bundle
import android.view.ViewGroup
import android.widget.Button
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import java.util.UUID

class MainActivity : Activity() {
    private lateinit var status: TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        if (Build.VERSION.SDK_INT >= 33) {
            requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS), 7101)
        }

        status = TextView(this).apply {
            textSize = 18f
            contentDescription = "Current Anvil Shell owner, team, state, and command"
            setPadding(32, 32, 32, 32)
        }
        val selfCheck = Button(this).apply {
            text = "Run deterministic self-check"
            contentDescription = "Queue a model-free Anvil Shell self-check"
            setOnClickListener {
                val intent = Intent(this@MainActivity, ShellSupervisorService::class.java).apply {
                    action = ShellSupervisorService.ACTION_ENQUEUE_SELF_CHECK
                    putExtra(ShellSupervisorService.EXTRA_ANVIL, "shell")
                    putExtra(ShellSupervisorService.EXTRA_TOKEN, UUID.randomUUID().toString())
                }
                startForegroundService(intent)
                status.text = "[shell][drew][adam][QUEUED] status"
            }
        }
        val refresh = Button(this).apply {
            text = "Read durable status"
            contentDescription = "Read the latest durable Anvil Shell job state"
            setOnClickListener { refreshStatus() }
        }
        val explanation = TextView(this).apply {
            text = """
                The window is disposable. Work is not.

                Commands enter a typed registry before execution. Hunger, Hyperbolic, Hugging Face, Adam, Vlad notes, explicit shell work, sessions, and anvil streams retain separate routes and authority.

                Checkpoint 1 proves the native supervisor and durable queue. Termux is a compatibility body during migration, not the state owner.
            """.trimIndent()
            textSize = 16f
            setPadding(32, 24, 32, 32)
        }
        val column = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            addView(status, ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT)
            addView(selfCheck, ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT)
            addView(refresh, ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT)
            addView(explanation, ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT)
        }
        setContentView(ScrollView(this).apply { addView(column) })
        refreshStatus()
    }

    override fun onResume() {
        super.onResume()
        refreshStatus()
    }

    private fun refreshStatus() {
        JobStore(this).use { status.text = it.latestSummary() }
    }
}
