package com.orren.android

import android.os.Bundle
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity

class MainActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val application = EditText(this).apply { setText("orren") }
        val inputTitle = EditText(this).apply { setText("default") }
        val output = TextView(this)
        val realize = Button(this).apply {
            text = "Realize state"
            setOnClickListener {
                output.text = NativeRealizationCore.process(application.text.toString(), inputTitle.text.toString())
                    .toRecords()
                    .joinToString("\n")
            }
        }
        setContentView(LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(32, 32, 32, 32)
            addView(application)
            addView(inputTitle)
            addView(realize)
            addView(output)
        })
    }
}

data class RealizationState(private val values: Map<String, String>) {
    fun toRecords(): List<String> = values.toSortedMap().map { (key, value) -> "$key=$value" }
}

object NativeRealizationCore {
    fun process(application: String, inputTitle: String): RealizationState =
        RealizationState(mapOf("application" to application, "input_title" to inputTitle))
}
