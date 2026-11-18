// QuPRS browser source-phase transport. MIT licensed adapter.
// Uses the original QuPRS MPFR C bridge and its exact-Clifford shortcuts;
// no binary64 conversion of the original rational phase is performed.
#ifndef QUPRS_BROWSER_PHASE_WEIGHTS_HPP
#define QUPRS_BROWSER_PHASE_WEIGHTS_HPP
#include <gmpxx.h>
#include <fstream>
#include <iostream>
#include <sstream>
#include <map>
#include <set>
#include <vector>
#include <array>
#include <string>
#include <cstdio>
#include <cstdlib>
#include <stdexcept>
#include <unistd.h>
#include <fcntl.h>
extern "C" int quprs_mpfr_phase_weight(const char*,const char*,const char*,const char*,unsigned long,char*,char*,size_t);
static std::string quprs_phase_temp;
static void quprs_phase_cleanup(){if(!quprs_phase_temp.empty())std::remove(quprs_phase_temp.c_str());}
static void quprs_phase_fail(const std::string& reason){std::cerr<<"QuPRS source-phase adapter: "<<reason<<std::endl;throw std::invalid_argument(reason);}
static std::string quprs_source_weights(const std::string& filename){
 std::ifstream source(filename);if(!source)return filename;
 std::map<int,std::pair<std::string,std::string>> weights;std::string line;int variables=-1;
 while(std::getline(source,line)){
  if(line.compare(0,6,"p cnf ")==0){std::istringstream in(line);std::string p,cnf;in>>p>>cnf>>variables;}
  if(line.compare(0,16,"c p quprs-phase ")!=0)continue;
  std::istringstream in(line);std::string c,p,tag,cn,cd,rn,rd,extra;int var,present;unsigned long bits;
  if(!(in>>c>>p>>tag>>var>>cn>>cd>>rn>>rd>>present>>bits)||(in>>extra)||var<=0||(present!=0&&present!=1)||bits<64||bits>1024||weights.count(var))quprs_phase_fail("invalid or duplicate phase descriptor");
  mpz_class denominator(cd),rad_denominator(rd);if(denominator<=0||rad_denominator<=0)quprs_phase_fail("nonpositive phase denominator");
  mpq_class cycles(mpz_class(cn),denominator);cycles.canonicalize();
  std::string re,im;
  if(!present && cycles==0){re="1.0";im="0.0";}
  else if(!present && cycles==mpq_class(1,2)){re="-1.0";im="0.0";}
  else if(!present && cycles==mpq_class(1,4)){re="0.0";im="1.0";}
  else if(!present && cycles==mpq_class(3,4)){re="0.0";im="-1.0";}
  else {
   std::array<char,512> r{},i{};int code=quprs_mpfr_phase_weight(cn.c_str(),cd.c_str(),rn.c_str(),rd.c_str(),bits,r.data(),i.data(),r.size());
   if(code!=0)quprs_phase_fail("original MPFR phase bridge failed: "+std::to_string(code));re=r.data();im=i.data();
  }
  weights.emplace(var,std::make_pair(re,im));
 }
 if(weights.empty())return filename;
 if(variables<0 || weights.rbegin()->first>variables)quprs_phase_fail("phase outside CNF variable range");
 std::string path;
#ifdef __EMSCRIPTEN__
 path="/tmp/quprs-source-phase.cnf";int fd=open(path.c_str(),O_CREAT|O_EXCL|O_WRONLY,0600);
#else
 const char* env=std::getenv("TMPDIR");path=std::string(env?env:"/tmp")+"/quprs-source-phase-XXXXXX";std::vector<char> name(path.begin(),path.end());name.push_back(0);int fd=mkstemp(name.data());path=name.data();
#endif
 if(fd<0)quprs_phase_fail("cannot create private phase-weight input");close(fd);quprs_phase_temp=path;std::atexit(quprs_phase_cleanup);
 std::ofstream output(path);if(!output)quprs_phase_fail("cannot write phase-weight input");std::set<int> seen;
 source.clear();source.seekg(0);
 while(std::getline(source,line)){
  if(line.compare(0,16,"c p quprs-phase ")==0)continue;
  if(line.compare(0,11,"c p weight ")==0){std::istringstream in(line);std::string c,p,weight;int literal;if(!(in>>c>>p>>weight>>literal))quprs_phase_fail("invalid positive weight line");auto it=weights.find(literal);if(literal>0 && it!=weights.end()){
    if(!seen.insert(literal).second)quprs_phase_fail("duplicate positive phase weight");output<<"c p weight "<<literal<<" "<<it->second.first<<" "<<it->second.second<<" 0\n";continue;
  }}
  output<<line<<"\n";
 }
 if(seen.size()!=weights.size())quprs_phase_fail("missing phase-weight placeholder");output.close();if(!output)quprs_phase_fail("phase-weight file write failed");
 std::cout<<"c o quprs-phase-weights "<<weights.size()<<std::endl;return path;
}
#endif
