#include <LeabraUnitSpec_cpp>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <iostream>
int main(int argc,char** argv) {
  if(argc!=2) return 2;
  std::ifstream input(argv[1]);
  if(!input) return 3;
  LeabraActFunSpec_cpp params;
  char kind;std::uint32_t in_bits,expected;std::size_t count=0,mismatches=0;
  while(input>>kind>>in_bits>>expected) {
    float x;std::memcpy(&x,&in_bits,sizeof(x));
    const float value=kind=='E'?GoNxx1FastExp(x):params.NoisyXX1(x);
    std::uint32_t bits;std::memcpy(&bits,&value,sizeof(bits));
    ++count;
    if(bits!=expected) {if(mismatches<10) std::cerr<<kind<<" x="<<x<<" actual="<<bits<<" expected="<<expected<<'\n';++mismatches;}
  }
  if(!input.eof()) return 4;
  std::cout<<"samples="<<count<<" mismatches="<<mismatches<<'\n';
  return mismatches!=0;
}
