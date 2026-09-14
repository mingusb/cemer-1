package main

import (
    "encoding/json"
    "os"
    "path/filepath"
    "strings"
    "testing"
    "github.com/emer/emergent/v2/etime"
    "github.com/emer/emergent/v2/looper"
)

type ReferenceRow struct {
    Trial, Cycle, Quarter int
    Plus bool
    Harmony float32
    Act, Ge, Gi, Vm, Noise, KFast, KMed, KSlow []float32
}

func removeGUI(callbacks *looper.NamedFuncs) {
    kept := (*callbacks)[:0]
    for _, callback := range *callbacks {
        if !strings.HasPrefix(callback.Name, "GUI") { kept = append(kept, callback) }
    }
    *callbacks = kept
}

func TestOriginalNeckerReference(t *testing.T) {
    directory := os.Getenv("NECKER_REFERENCE_OUTPUT")
    if directory == "" { t.Fatal("NECKER_REFERENCE_OUTPUT is required") }
    if err := os.MkdirAll(directory, 0755); err != nil { t.Fatal(err) }
    for _, scenario := range []struct{Name string; Noise float32; Adapt bool; Cycles int}{
        {"zero-noise",0,false,100},
        {"zero-noise-adaptation",0,true,1000},
        {"authored-default",.01,false,100},
        {"authored-high-noise",.1,false,100},
        {"authored-low-noise",.001,false,100},
        {"authored-adaptation",.01,true,1000},
        {"authored-long-no-adaptation",.01,false,1000},
    } {
        t.Run(scenario.Name, func(t *testing.T) {
            sim := &Sim{}
            sim.New()
            sim.ConfigAll()
            // Match controls changed after ConfigAll: retain original quarter
            // event updates and actual PlusPhase timing in the authored program.
            sim.Noise = scenario.Noise
            sim.KNaAdapt = scenario.Adapt
            sim.Cycles = scenario.Cycles
            for _, stack := range sim.Loops.Stacks {
                removeGUI(&stack.OnInit)
                for _, loop := range stack.Loops {
                    removeGUI(&loop.OnStart)
                    removeGUI(&loop.OnEnd)
                }
            }
            sim.Init()
            rows := []ReferenceRow{}
            count := 0
            sim.Loops.Loop(etime.Test, etime.Cycle).OnEnd.Add("ReferenceObserver", func() {
                trial := sim.Loops.Loop(etime.Test, etime.Trial).Counter.Cur
                count++
                // Retain every cycle for cross-language lifecycle validation.
                row := ReferenceRow{Trial:trial,Cycle:sim.Context.Cycle,Quarter:int(sim.Context.Quarter),Plus:sim.Context.PlusPhase,Harmony:sim.Harmony(sim.Net)}
                for _, neuron := range sim.Net.Layers[0].Neurons {
                    row.Act=append(row.Act,neuron.Act);row.Ge=append(row.Ge,neuron.Ge)
                    row.Gi=append(row.Gi,neuron.Gi);row.Vm=append(row.Vm,neuron.Vm)
                    row.Noise=append(row.Noise,neuron.Noise)
                    row.KFast=append(row.KFast,neuron.GknaFast);row.KMed=append(row.KMed,neuron.GknaMed);row.KSlow=append(row.KSlow,neuron.GknaSlow)
                }
                rows=append(rows,row)
            })
            sim.Loops.ResetAndRun(etime.Test)
            if count != 100*scenario.Cycles { t.Fatalf("original loop ran %d cycles, expected%d",count,100*scenario.Cycles) }
            output := struct {Name string; TotalCycles int; Rows []ReferenceRow}{scenario.Name,count,rows}
            bytes,err := json.MarshalIndent(output,"","  ");if err!=nil {t.Fatal(err)}
            if err=os.WriteFile(filepath.Join(directory,scenario.Name+".json"),bytes,0644);err!=nil {t.Fatal(err)}
            t.Logf("captured %d/%d cycles from all100 authored trials",len(rows),count)
        })
    }
}
